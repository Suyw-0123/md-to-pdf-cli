# 架構

這一頁說明整體設計與協調膠水。每個階段都有自己的深入頁面；這裡是把它們串起來的地圖。

## 設計原則

1. **單一自包含 HTML 字串。** 瀏覽器需要的一切——主題 CSS、Pygments CSS、KaTeX
   （含以 data URI 內嵌的字型）、mermaid——全部內嵌進一份 HTML 文件。轉檔完全離線、
   可重現；沒有任何 CDN 抓取、沒有外部樣式表／字型請求。
2. **能決定性就放 server 端，必要時才放瀏覽器端。** 程式碼高亮由 Python 的 Pygments
   完成（決定性、不受瀏覽器差異影響）。數學（KaTeX）與圖表（mermaid）需要 JS runtime，
   所以在 Chromium 裡跑，而且我們會*等*它們完成再列印。
3. **路徑相對於 Markdown 檔解析，而非 CWD。** 圖片等資源相對於來源 `.md` 所在目錄解析，
   所以在任何地方執行都能正常運作。
4. **明確優先序：** CLI 旗標 > 設定檔 > 內建預設。

## 協調者：`converter.convert()`

`src/md2pdf/converter.py` 刻意保持很小——它是唯一能一眼看到整個流程的地方：

```python
def convert(input_path, output_path, config) -> ConversionResult:
    source = read_markdown(input_path)                       # 1. 讀檔（utf-8-sig）
    doc = render_markdown(source, config.features, ...)      # 2. md -> html body
    doc.html = rewrite_image_sources(doc.html, md_dir, ...)  # 3. 修圖片 src
    html = build_html(doc, config)                           # 4. 組 HTML
    render_pdf(html, out, config)                            # 5. Chromium -> PDF
    return ConversionResult(...)
```

追 bug 時，先判斷症狀屬於這五個呼叫中的哪一個，再跳到對應模組的 wiki 頁。

### 階段 1 — `read_markdown()`

以 `encoding="utf-8-sig"` 讀檔。`-sig` 變體會在有 BOM 時透明地去除它。這是**中文亂碼
bug** 的修法：外洩的 BOM 或被誤判的編碼會破壞開頭幾個字元。

### 階段 2 — `render_markdown()`

Markdown → HTML *body 片段*（不是完整文件）加上 metadata：文件 `title`（來自 front-matter
的 `title:` 或第一個 H1）、`headings` 清單、以及可選的 TOC。見
[Markdown 渲染](Markdown-Rendering.md)。

### 階段 3 — `rewrite_image_sources()`

改寫每個 `<img src>`，使其在列印時能解析：相對路徑變絕對 `file://` URL（或在開啟
`embed_images` 時變成 base64 data URI）。見[圖片](Images.md)。

### 階段 4 — `build_html()`

渲染 Jinja2 模板、內嵌所有 CSS/JS/字型資產，產出單一 HTML 字串。見
[HTML 與資產](HTML-and-Assets.md)。

### 階段 5 — `render_pdf()`

啟動 Chromium、導向 HTML 的暫存 `file://` 副本、等待 `window.__md2pdf_ready` 旗標，
再呼叫 `page.pdf()`。見 [PDF 渲染](PDF-Rendering.md)。

## 在管線中流動的資料物件

- **`Config`**（`config.py`）——完全合併後的設定。在 CLI 層建一次，貫穿每個階段。
- **`RenderedDoc`**（`markdown_render.py`）——`html`、`title`、`headings`、
  `toc_html`。注意 `html` 會在階段 3 被就地改寫。
- **`ConversionResult`**（`converter.py`）——`input_path`、`output_path`、
  `title`；回傳給 CLI 顯示成功訊息。

## 為什麼階段 2 回傳 body 片段而非完整 HTML

把 Markdown 渲染器的輸出保持為*片段*，代表只有一個地方（`html_template.py`）負責
`<head>`、資產內嵌、語言屬性、TOC 擺放、以及 readiness 腳本。渲染器專注於內容；
模板負責呈現與瀏覽器契約。

## 失敗處理

CLI（`cli.py`）攔截三類錯誤，轉成乾淨、有顏色的訊息並以 exit code 1 結束：

- `BrowserNotInstalledError`——缺 Chromium；以黃色印出安裝提示。
- `FileNotFoundError`——輸入檔或 `--config` 路徑錯誤。
- 其他任何 `Exception`——以 `Conversion failed: …` 呈現，而非 traceback。
