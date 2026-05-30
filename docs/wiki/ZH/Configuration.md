# 設定（`config.py`）

設定是一組 dataclass，從 `md2pdf.toml` 檔案載入（透過標準庫 `tomllib`），上面再疊上
內建預設與 CLI 覆寫。

## 優先序

```
CLI 旗標  >  md2pdf.toml  >  內建 dataclass 預設
```

`config.py` 負責下兩層（預設 + 檔案）。CLI 層（`cli.py` 的 `_apply_overrides`）負責最上層。
`load_config()` 永遠看不到 CLI 旗標——請保持這個分離。

## 載入

- `find_config_file(explicit, start)`（config.py:168）：明確的 `--config` 路徑優先
  （找不到會拋 `FileNotFoundError`）；否則在 CWD 找 `md2pdf.toml`。找不到任何設定檔
  → 用內建預設。
- `load_config()`（config.py:178）：讀 TOML 並透過 `Config.from_dict(data, base_dir=...)`
  建出 `Config`。`base_dir` 是**設定檔所在目錄**，用來解析相對的 CSS 路徑。

## Schema

所有區段皆為可選；每個 dataclass 都有 `from_dict` classmethod，會用預設補齊缺少的鍵、
並做防禦性型別轉換。

### `[output]` → `OutputConfig`

| 鍵 | 預設 | 說明 |
|----|------|------|
| `page_size` | `"A4"` | 以 `format` 傳給 Chromium。`A4`、`Letter`、`Legal`… |
| `landscape` | `false` | 方向。 |
| `margin` | `2cm / 2cm / 1.8cm / 1.8cm` | `Margin` dataclass；TOML inline table。 |

`Margin.as_playwright()` 回傳 `page.pdf()` 需要的 dict 形狀。

### `[theme]` → `ThemeConfig`

| 鍵 | 預設 | 說明 |
|----|------|------|
| `base` | `"default"` | 保留給未來的具名主題。 |
| `css` | `[]` | 額外 CSS 檔，附加在預設主題後（後者贏）。單一字串會被包成 list。 |
| `font_family` | `DEFAULT_FONT_FAMILY` | CSS 字型堆疊；CJK 字型排前面。 |
| `code_style` | `"default"` | 任何 Pygments style 名稱。 |

`DEFAULT_FONT_FAMILY`（config.py:16）把 `Noto Sans CJK TC/SC`、`Microsoft JhengHei`、
`PingFang TC` 等排*在最前面*，讓中文用真正的 CJK 字型渲染而非 tofu 方塊。這是 CJK
正確性的一環。

### `[features]` → `FeaturesConfig`

| 鍵 | 預設 | 效果 |
|----|------|------|
| `math` | `true` | 啟用 dollarmath 解析 + KaTeX 注入。 |
| `mermaid` | `true` | 注入 mermaid runtime + 渲染 `pre.mermaid`。 |
| `toc` | `false` | 產生目錄頁。 |
| `embed_images` | `false` | 把本地圖片內嵌為 base64 data URI。 |

### `[header]` / `[footer]` → `BannerConfig`

`enabled` + `template`（內層 HTML）。**頁腳預設為啟用**，使用置中的 `current / total`
頁碼模板；頁眉預設關閉。模板可使用 Chromium 的佔位 class：`title`、`date`、`url`、
`pageNumber`、`totalPages`。它們如何被包裝與渲染見 [PDF 渲染](PDF-Rendering.md)。

## CSS 路徑解析

`Config.resolved_css_paths()`（config.py:159）把每個 `theme.css` 條目轉成絕對路徑：
絕對路徑直接通過；相對路徑相對於 `base_dir`（設定檔目錄）解析。**例外：** 透過 CLI
`--css` 旗標加入的 CSS，在 `cli.py` 中已先相對 CWD 解析過再附加，因為那時可能根本沒有
設定檔可當錨點。

## 新增一個設定（檢查清單）

1. 在對的 dataclass 加上欄位（含預設）。
2. 在該 dataclass 的 `from_dict` 讀取並轉型。
3. 若要在 CLI 對使用者開放，於 `cli.py` 加一個 Typer `Option`，並在 `_apply_overrides`
   加一個分支。
4. 若會影響渲染，把它接進對應階段（`markdown_render`、`html_template` 或 `pdf_render`）。
5. 加進 `cli.py` 的 `_SAMPLE_TOML`，並在 README 記錄。
6. 在 `tests/test_config.py` 新增／擴充測試。
