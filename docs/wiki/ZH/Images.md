# 圖片（`images.py`）

這個模組修掉經典的**「轉檔後破圖」bug**——就是那種在編輯器預覽正常、轉成 PDF 卻空白的
情況。它改寫渲染後 HTML 裡每個 `<img src>`，讓來源在列印時能正確解析。

## 問題

像 `![](../figures/plot.png)` 這樣的 Markdown 帶的是相對於 `.md` 檔的路徑。等 HTML
到了 Chromium 時，它是從一個暫存目錄載入的，所以裸的相對路徑不再指向任何地方。而且
基於安全，Chromium 不會從 origin 為 `about:blank` 的頁面載入 `file://` 圖片
（"Not allowed to load local resource"）。這兩件事一起造成空白圖片。

`images.py` 處理路徑這一半；`pdf_render.py` 處理 origin 那一半（它從真正的 `file://`
文件載入頁面——見 [PDF 渲染](PDF-Rendering.md)）。

## 它做什麼

`rewrite_image_sources(html_body, base_dir, *, embed=False)`（images.py:38）用一個
regex 掃過 `<img …src="…">` 標籤，並改寫每個本地來源：

1. **跳過遠端／已是絕對的來源。** `_REMOTE` 樣式匹配 `http:`、`https:`、`data:`、
   `file:` 與協定相對的 `//`——這些原樣保留（遠端圖片由 Chromium 在渲染時抓取）。
2. **解析相對路徑**，相對於 `base_dir`（來源 `.md` 檔所在目錄），並展開 `~`。
3. **若檔案不存在**，刻意把來源*原樣保留*，讓壞掉的參照保持可見／可除錯，而非默默丟掉。
4. **否則改寫**成下列之一：
   - `file://` 絕對 URL（預設），或
   - base64 `data:` URI（當 `embed=True`，即 `embed_images` / `--embed-images`）。

`embed=True` 就是產生**完全自包含 PDF** 的關鍵——位元組被烤進 HTML，列印時沒有任何外部
檔案參照。代價是中間的 HTML 字串較大。

## 實作註記

- `<img>` 匹配器（`_IMG_SRC`）處理單／雙引號的 `src`，並用 `DOTALL` 讓跨行標籤也能匹配。
  它刻意只動 `src`。
- `_to_file_url()` 組出 `file://` + `quote(path)`，讓空白與非 ASCII 路徑字元被
  百分號編碼。
- `_to_data_uri()` 從檔名猜 MIME 型別（退回 `application/octet-stream`）並 base64 編碼
  位元組。讀檔失敗則回傳 `None`，呼叫端退回 `file://` URL。
- 這個模組純粹操作 HTML 字串——沒有瀏覽器或設定依賴，所以容易單元測試
  （`tests/test_images.py`）。

## 相關測試

`tests/test_converter.py::test_relative_parent_image_loads` 是一個端到端回歸測試
（標記 `slow`），它轉換一份參照 `../` 相對圖片的 Markdown，並斷言它確實內嵌／載入——
這是防止破圖 bug 復發的守衛。
