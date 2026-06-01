# PDF 渲染（`pdf_render.py`）

最後一個階段：透過 [Playwright](https://playwright.dev/python/) 驅動 headless Chromium，
把自包含 HTML 變成 PDF。這個模組很小，卻握有整個專案最重要的兩個正確性決策。

## `render_pdf(html, output_path, config)`（pdf_render.py:59）

```python
with sync_playwright() as p:
    browser = _launch_chromium(p)
    page = browser.new_page()
    with tempfile.TemporaryDirectory(prefix="md2pdf-") as tmpdir:
        tmp_html = Path(tmpdir) / "document.html"
        tmp_html.write_text(html, encoding="utf-8")
        page.goto(tmp_html.as_uri(), wait_until="load")
        page.wait_for_function("window.__md2pdf_ready === true", timeout=30_000)
        page.emulate_media(media="print")
        page.pdf(**pdf_kwargs)
```

### 關鍵決策 #1 — 從暫存 `file://` 頁面載入，而非 `set_content()`

最直覺的做法 `page.set_content(html)` 會讓頁面 origin 是 `about:blank`。Chromium 接著
**拒絕載入本地 `file://` 圖片**（"Not allowed to load local resource"），於是每張本地圖片
都空白——就是破圖 bug。而從真正的 `file://` URL 提供的頁面*可以*載入 `file://` 子資源。
所以我們把 HTML 寫到暫存檔，再 `page.goto()` 它的 `file://` URI。這一點，搭配
[圖片](Images.md) 把 src 改寫成絕對 `file://`，正是讓本地圖片能運作的原因。

### 關鍵決策 #2 — 等待 `window.__md2pdf_ready`

`page.pdf()` 要等到 `wait_for_function` 確認 `window.__md2pdf_ready === true` 才呼叫。
那個旗標由模板的 readiness 腳本在 KaTeX、mermaid、字型載入都完成後才設定（見
[HTML 與資產](HTML-and-Assets.md)）。沒有這個等待，PDF 經常會擷取到數學未排版或圖表未
渲染的頁面。逾時是 `_RENDER_TIMEOUT_MS = 30_000`（30 秒）——若渲染卡超過這個時間，
`wait_for_function` 會拋錯，CLI 回報乾淨的失敗。

`page.emulate_media(media="print")` 確保列印 CSS（`@page`、`print-color-adjust` 等）在
擷取前生效。

## `page.pdf()` 選項

`pdf_kwargs`（pdf_render.py:66）把設定對應到 Playwright：

| 選項 | 值 | 原因 |
|------|----|------|
| `format` | `config.output.page_size` | A4/Letter/… |
| `landscape` | `config.output.landscape` | 方向 |
| `margin` | `config.output.margin.as_playwright()` | 各邊邊界 |
| `print_background` | `True` | 印出背景色／網底 |
| `prefer_css_page_size` | `False` | 上面的 `format` 勝過任何 `@page size` |
| `tagged` | `True` | 無障礙／tagged PDF——大綱**必需** |
| `outline` | `True` | 輸出 heading 書籤 |

> **書籤陷阱：** 只設 `outline=True` 會產生*空的*大綱。Chromium 只在 **tagged** PDF
> 才輸出 heading 大綱，所以 `tagged=True` 也是必需。兩個都要留。

## 頁眉、頁腳與頁碼

Chromium **不**支援 CSS running header（`@page @top-center`）。頁面裝飾必須走
`display_header_footer` + `header_template` / `footer_template`。當
`config.header.enabled or config.footer.enabled` 時：

- `_wrap_banner(inner)`（pdf_render.py:46）把使用者的內層 HTML 包進一個有明確
  `font-size:9px`、滿版寬度、padding、淡色、置中文字的 `<div>`。**這個明確尺寸是強制的**
  ——Chromium 用近乎 0 的預設字級渲染頁眉／頁腳模板，所以沒包過的模板實際上看不見。
- 被關閉的那一側仍需要一個佔位（`_EMPTY_BANNER = "<span></span>"`），否則 Chromium 會
  顯示它自己的預設（例如 URL／日期）。
- 模板使用 Chromium 的佔位 class：`pageNumber`、`totalPages`、`title`、`date`、`url`。
  預設頁腳是 `pageNumber / totalPages`。

## 瀏覽器未安裝的處理（自動安裝）

Chromium 不是 pip 依賴，而是 Playwright 的瀏覽器二進位檔。為了讓
`pip install md-to-pdf-cli` 開箱即用，md2pdf 會在首次使用時自動下載它：

`_launch_chromium()`（pdf_render.py）先嘗試 `playwright.chromium.launch()`。失敗時用
`_is_missing_browser_error()` 判斷錯誤（比對 `Executable doesn't exist` /
`playwright install`），不相關的錯誤原樣往外拋。若確實是瀏覽器缺失，就呼叫
`_install_chromium()`，它以目前的直譯器（`sys.executable`）執行
`python -m playwright install chromium`，因此在 pip、uv、pipx 安裝下行為一致——二進位檔
落在 Playwright 共用的每使用者快取，所以只會下載一次。接著重試啟動。

可用 `MD2PDF_AUTO_INSTALL_BROWSER=0` 關閉自動安裝（CI 中很方便）。當自動安裝關閉或下載
失敗時，拋出 `BrowserNotInstalledError`，帶著 `_INSTALL_HINT` 文字，CLI 以黃色印出該提示
而非裸 traceback。提示使用已發布的套件名稱，所以 uv-tool 版本為
`uv tool run --from md-to-pdf-cli playwright install chromium`。

## 生命週期

瀏覽器一律在 `finally` 中關閉，暫存目錄由其 context manager 清掉，所以即使失敗也不會
殘留 Chromium 程序或暫存檔。
