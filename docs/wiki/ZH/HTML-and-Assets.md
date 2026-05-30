# HTML 與資產（`html_template.py`、`assets/`）

這個階段把 Markdown body 片段 + 設定組成**一份自包含 HTML 文件**。「自包含」正是重點：
每個樣式表、腳本、字型都內嵌，讓頁面從任何 origin 都渲染一致，且轉檔完全不碰網路。

## `build_html(doc, config)`（html_template.py:57）

它讀資產、建一個 context dict、渲染 Jinja2 模板：

| Context 鍵 | 來源 |
|------------|------|
| `body` | `doc.html`（渲染後的片段） |
| `title`、`toc_html` | 來自 `RenderedDoc` |
| `theme_css` | `assets/default.css` |
| `extra_css` | 來自 `config.resolved_css_paths()` 串接的使用者 CSS |
| `pygments_css` | `pygments_css(config.theme.code_style)` |
| `font_family` | `config.theme.font_family`，注入為 `--md2pdf-font` |
| `katex_css` / `katex_js` / `katex_autorender_js` | 僅在 `features.math` 時 |
| `mermaid_js` | 僅在 `features.mermaid` 時 |

資產檔透過 `importlib.resources.files("md2pdf") / "assets"`（html_template.py:21）從
已安裝的套件讀取——絕不用相對檔案系統路徑——所以裝成 wheel 後也一樣可用。

## 模板（`assets/template.html.j2`）

一份精簡的 HTML5 文件。`<head>` 裡順序很重要：

1. KaTeX CSS（若有數學）→ 2. Pygments CSS → 3. 主題 CSS → 4. `--md2pdf-font` 變數
→ 5. 使用者額外 CSS **放最後**（讓它能覆寫一切）。

`<body>` 包含可選的 TOC `<nav>`，再來是含 body 的 `<main class="md2pdf-content">`。
結尾是 KaTeX 與 mermaid 的腳本（各自被功能旗標守住）以及 **readiness 腳本**。

### Readiness 契約：`window.__md2pdf_ready`

這是防止「太早列印／畫一半」PDF 的關鍵。一個 async IIFE：

1. 對 `document.body` 跑 KaTeX auto-render（分隔符：`\[ \]`、`\( \)`、`$$`、`$`；
   `throwOnError: false`），
2. 初始化 mermaid（`startOnLoad: false`、`securityLevel: "loose"`），並對所有
   `pre.mermaid` 節點 `await mermaid.run()`，
3. `await document.fonts.ready`，
4. 設 `window.__md2pdf_ready = true`。

`pdf_render.py` 在呼叫 `page.pdf()` 前正是等這個旗標。若你新增另一個 async 渲染步驟，
請在旗標被設定**之前**做，否則 PDF 可能擷取到未完成的頁面。見
[PDF 渲染](PDF-Rendering.md)。

## 把 KaTeX 字型內嵌為 data URI

`_katex_css_inlined()`（html_template.py:34）讀 `katex.min.css`，並用 `_FONT_URL`
regex 把每個 `url(fonts/Foo.woff2)` 改寫成 base64 `data:font/woff2` URI。沒有這一步，
KaTeX 字符會看不見：頁面沒有能解析 `fonts/…` 的 base URL，而 Chromium 會擋掉那些子資源。
只 vendored `.woff2`（每個現代 Chromium 都支援），讓 bundle 維持小。結果會被 `lru_cache`
快取，因為每次都相同。

## `assets/default.css` — 分頁媒體主題

這份樣式表編碼了大多數「保真度修正」。重點：

- **表格跨頁：** `thead { display: table-header-group }` 讓表頭在每頁重複；
  `tr, td, th { break-inside: avoid }` 阻止列被切斷。這修掉**表格截斷 bug**。
- **圖片：** `max-width: 100%`、`height: auto`、`break-inside: avoid`——不溢出頁面、
  不被切割。
- **標題：** `break-after: avoid`，讓標題不會落單在頁底。
- **程式碼：** `pre.highlight` 樣式搭配 `white-space: pre-wrap` + `word-break`，讓長行
  換行而非溢出；`.highlight` 選擇器正是 Pygments CSS 落地之處。
- **CJK：** `--md2pdf-font`（由設定驅動、CJK 優先）與一組 CJK 友善的 monospace 堆疊
  （`--md2pdf-mono`）。
- **TOC：** `nav.toc { break-after: page }`，讓目錄自成一頁。
- `-webkit-print-color-adjust: exact`，讓背景／顏色真的會印出來。

CSS 自訂屬性（`--md2pdf-*`）是受支援的擴充面：最後載入的使用者 `theme.css`（或 `--css`）
可覆寫其中任何一個，而不必整份替換。

## Vendored 資產

位於 `assets/vendor/`：

- **KaTeX**（`katex.min.css`、`katex.min.js`、`contrib/auto-render.min.js`、與
  `fonts/*.woff2`）。
- **mermaid**（`mermaid.min.js`）——會設定 `globalThis.mermaid`。

這些是釘版、離線的副本。要升級就替換檔案（KaTeX 的 woff2 字型集要保持完整），並重跑
端到端測試確認渲染仍能完成、`__md2pdf_ready` 仍會被達到。

## Trusted-HTML 註記

Jinja2 的 `Environment` 用 `autoescape=False`（html_template.py:53）是**刻意的**：body、
CSS、JS 全是我們產生的、已跳脫／可信的內容，自動跳脫它們會破壞內嵌的腳本與樣式。
不要把不可信字串直接餵進模板 context。
