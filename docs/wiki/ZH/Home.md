# md-to-pdf-cli — 開發者技術文件

`md-to-pdf-cli` 使用 **headless Chromium** 作為渲染引擎，把本地 Markdown 檔案轉成
PDF。套件在 PyPI 上的名稱是 `md-to-pdf-cli`，但 import 套件名與 CLI 指令都是
`md2pdf`。

這份 wiki 是寫給專案的*開發者*（你、未來的你、以及其他貢獻者）。它說明程式如何組織、
關鍵決策為什麼這樣做、以及要修改某個東西時該往哪看。*使用方式*請看最上層的
[`README.md`](../../../README.md)。

## 為什麼有這個工具

它是為了修掉其他 Markdown→PDF 工具常見的保真度 bug 而做的：

- **中文／CJK 亂碼（mojibake）** — 以 `utf-8-sig` 讀檔、並內建 CJK 優先的字型堆疊來解決。
- **表格跨頁被截斷** — 以分頁 CSS 解決
  （`thead { display: table-header-group }`、`break-inside: avoid`）。
- **轉檔後破圖**（在編輯器預覽明明正常）— 以「從真正的 `file://` 文件載入頁面」解決，
  這樣 Chromium 才願意載入本地圖片子資源。

選 Chromium 是刻意的：它和多數 Markdown 編輯器預覽用的是同一個引擎，所以「預覽正常、
轉檔破版」的問題大致消失，而且程式碼高亮／數學／mermaid 都能原生運作，不需要第二段
預渲染。

## 管線總覽

```
.md 檔
  │  read_markdown()  ── utf-8-sig（去除 BOM → 修中文亂碼）
  ▼
render_markdown()    ── markdown-it-py + 外掛；Pygments 高亮（server-side）
  │  HTML body 片段 + 標題 + 各 heading + 可選 TOC
  ▼
rewrite_image_sources()  ── 相對 <img src> → 絕對 file:// 或 data URI
  ▼
build_html()         ── Jinja2 模板；內嵌「所有」資產（CSS、KaTeX+字型、mermaid）
  │  一份自包含的 HTML 字串
  ▼
render_pdf()         ── Chromium：goto(暫存 file://) → 等 __md2pdf_ready → page.pdf()
  ▼
.pdf 檔
```

`converter.convert()` 是把這五個階段串起來的協調者
（[converter.py](PDF-Rendering.md) 依序呼叫它們）。

## 模組地圖

| 模組 | 職責 | wiki 頁面 |
|------|------|-----------|
| `cli.py` | Typer CLI、預設指令簡寫、旗標覆寫、`init` | [CLI](CLI.md) |
| `config.py` | dataclass schema、TOML 載入、優先序規則 | [設定](Configuration.md) |
| `converter.py` | 協調 md → html → pdf | [架構](Architecture.md) |
| `markdown_render.py` | Markdown → HTML、Pygments 高亮、數學、mermaid、TOC | [Markdown 渲染](Markdown-Rendering.md) |
| `images.py` | 改寫 `<img src>`，使其在列印時能解析／內嵌 | [圖片](Images.md) |
| `html_template.py` | 組出單一自包含 HTML 文件 | [HTML 與資產](HTML-and-Assets.md) |
| `pdf_render.py` | 驅動 Chromium、等待渲染、輸出 PDF | [PDF 渲染](PDF-Rendering.md) |
| `assets/` | 模板、預設主題 CSS、vendored KaTeX + mermaid | [HTML 與資產](HTML-and-Assets.md) |

## 從哪裡開始讀

- 初次接觸這份程式碼？先讀[架構](Architecture.md)，再沿著管線一頁一頁看。
- 要改 CLI 行為或旗標？→ [CLI](CLI.md) + [設定](Configuration.md)。
- 渲染 bug（數學／mermaid／程式碼／表格）？→ [Markdown 渲染](Markdown-Rendering.md)
  與 [HTML 與資產](HTML-and-Assets.md)。
- 「空白 PDF／破圖／卡住」的 bug？→ [PDF 渲染](PDF-Rendering.md)。
- 設定環境或跑測試？→ [開發](Development.md)。

## 專案事實

- **Python**：3.12+（用到標準庫 `tomllib`）。
- **套件管理**：所有事情都用 [`uv`](Development.md)——依賴、執行、打包、發布。
  本 repo 不要直接用 `pip`／`venv`。
- **執行期依賴**：`markdown-it-py`、`mdit-py-plugins`、`pygments`、`jinja2`、
  `playwright`、`typer`。
- **Chromium 不是 pip 依賴**——它是 Playwright 一次性下載
  （`playwright install chromium`）到共用快取的瀏覽器二進位檔。
- **授權**：MIT。
