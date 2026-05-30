# Markdown 渲染（`markdown_render.py`）

這個階段把 Markdown 原始碼變成 **HTML body 片段**加上 metadata（`RenderedDoc`：
`html`、`title`、`headings`、`toc_html`）。它建構在
[markdown-it-py](https://github.com/executablebooks/markdown-it-py) 與
[mdit-py-plugins](https://github.com/executablebooks/mdit-py-plugins) 之上。

## 解析器

`build_parser(features)`（markdown_render.py:85）設定一個 CommonMark 解析器並疊上外掛：

```python
md = MarkdownIt("commonmark", {"highlight": _highlight})
md.enable(["table", "strikethrough"])
md.use(front_matter_plugin)   # YAML front-matter（用於 title:）
md.use(footnote_plugin)       # [^1] 註腳
md.use(deflist_plugin)        # 定義列表
md.use(tasklists_plugin, enabled=True)   # - [ ] / - [x] 勾選框
md.use(anchors_plugin, min_level=1, max_level=3)  # heading id="" 錨點（TOC + 書籤）
if features.math:
    md.use(dollarmath_plugin, double_inline=True, renderer=_math_renderer)
```

`highlight` callback 在建構時就接上，所以 fenced code block 在渲染期間就被高亮。

## 程式碼高亮（server-side，Pygments）

`_highlight(code, lang, attrs)`（markdown_render.py:56）：

- `mermaid` fence **不**會被高亮——它原樣輸出為
  `<pre class="mermaid">…跳脫過的原始碼…</pre>`，交給瀏覽器端的 mermaid runtime。
- 否則以語言名稱查 lexer，失敗則退回 `guess_lexer`，再退回純 `text` lexer。
- 它用 `HtmlFormatter(nowrap=True)`，只輸出 token 的 `<span>`，再自己包成
  `<pre class="highlight"><code>…</code></pre>`。

**為什麼要 `nowrap=True` + 自己包？** Pygments 預設 formatter 會把輸出包進自己的
`<div class="highlight"><pre>…`。把那個從 markdown-it 的 `highlight` callback 回傳
會造成雙重包裹（markdown-it 也會包 fence 輸出），產生巢狀 `<pre>` 與壞掉的樣式。
`nowrap=True` 只給我們上色的 span，讓我們自己掌控 CSS 所瞄準的那一層包裹。

`pygments_css(style)`（markdown_render.py:76）產出限定在 `.highlight` 範圍內的樣式規則，
由 `html_template` 內嵌。未知的 style 名稱會退回 `default`。

## 數學

當 `features.math` 開啟時，`dollarmath` 外掛解析 `$inline$` 與 `$$block$$`。
`_math_renderer`（markdown_render.py:49）輸出 KaTeX 風格的分隔符——行內用 `\(…\)`、
顯示用 `\[…\]`——而不是自己渲染數學。真正的排版在瀏覽器裡由 KaTeX auto-render 完成
（見 [HTML 與資產](HTML-and-Assets.md)）。`double_inline=True` 讓單行的 `$$…$$` 也能
被當成顯示數學。

> 瀏覽器的 auto-render 設定也認得原始的 `$…$`／`$$…$$`，所以即使解析器已轉成
> `\(…\)`／`\[…\]`，數學仍可運作。

## Mermaid

除了 `_highlight` 裡的原樣輸出，沒有 server 端工作。`<pre class="mermaid">` 區塊由
Chromium 裡的 mermaid.js 渲染成 SVG。

## 標題、heading 與 TOC

- `_extract_front_matter_title()` 在 YAML front-matter 找 `title:` 行。
- 否則標題取第一個 H1 的文字，再否則用 `fallback_title`（輸入檔名主幹，由 `converter`
  傳入）。
- `_collect_headings()` 走訪 token 串流，把 `heading_open` token 與其 `inline` 文字配對，
  並讀取 anchors 外掛指派的 `id`。
- `_build_toc_html()`（僅在 `features.toc` 時）輸出 `<nav class="toc">`，內含 H1–H3 的
  縮排連結。注意 TOC 標題是寫死的字串 `目錄`——若需要在地化／可設定，改這裡。

heading 錨點身兼兩職：文件內 TOC 連結，**以及** Chromium 產生 PDF 書籤大綱的來源。

## 輸出契約

`render_markdown()` 回傳一個 `RenderedDoc`。它的 `.html` 是**片段**（沒有
`<html>`／`<head>`／`<body>`）。完整文件稍後由 `html_template.build_html()` 組出。
請把呈現／`<head>` 相關的事情留在這個模組之外。
