# Markdown Rendering (`markdown_render.py`)

This stage turns Markdown source into an **HTML body fragment** plus metadata
(`RenderedDoc`: `html`, `title`, `headings`, `toc_html`). It is built on
[markdown-it-py](https://github.com/executablebooks/markdown-it-py) and
[mdit-py-plugins](https://github.com/executablebooks/mdit-py-plugins).

## The parser

`build_parser(features)` (markdown_render.py:85) configures a CommonMark parser
and layers on plugins:

```python
md = MarkdownIt("commonmark", {"highlight": _highlight})
md.enable(["table", "strikethrough"])
md.use(front_matter_plugin)   # YAML front-matter (used for title:)
md.use(footnote_plugin)       # [^1] footnotes
md.use(deflist_plugin)        # definition lists
md.use(tasklists_plugin, enabled=True)   # - [ ] / - [x] checkboxes
md.use(anchors_plugin, min_level=1, max_level=3)  # heading id="" anchors (TOC + bookmarks)
if features.math:
    md.use(dollarmath_plugin, double_inline=True, renderer=_math_renderer)
```

The `highlight` callback is wired at construction so fenced code blocks are
highlighted during rendering.

## Code highlighting (server-side, Pygments)

`_highlight(code, lang, attrs)` (markdown_render.py:56):

- A `mermaid` fence is **not** highlighted — it is passed through as
  `<pre class="mermaid">…escaped source…</pre>` for the browser-side mermaid
  runtime.
- Otherwise it looks up the lexer by language name, falling back to
  `guess_lexer`, then to the plain `text` lexer.
- It uses `HtmlFormatter(nowrap=True)`, which emits only the token `<span>`s, and
  wraps them itself in `<pre class="highlight"><code>…</code></pre>`.

**Why `nowrap=True` + a manual wrapper?** Pygments' default formatter wraps
output in its own `<div class="highlight"><pre>…`. Returning that from a
markdown-it `highlight` callback causes double-wrapping (markdown-it also wraps
fence output), producing nested `<pre>` and broken styling. `nowrap=True` gives
us just the colored spans so we control the single wrapper that the CSS targets.

`pygments_css(style)` (markdown_render.py:76) produces the style rules, scoped to
`.highlight`, that `html_template` inlines. An unknown style name falls back to
`default`.

## Math

When `features.math` is on, the `dollarmath` plugin parses `$inline$` and
`$$block$$`. `_math_renderer` (markdown_render.py:49) emits KaTeX-style
delimiters — `\(…\)` for inline, `\[…\]` for display — rather than rendering math
itself. The actual typesetting happens in the browser via KaTeX auto-render (see
[HTML & Assets](HTML-and-Assets.md)). `double_inline=True` allows `$$…$$` on a
single line to be treated as display math.

> The browser's auto-render config also recognizes raw `$…$`/`$$…$$`, so math
> works even though the parser already converted to `\(…\)`/`\[…\]`.

## Mermaid

No server-side work beyond the passthrough in `_highlight`. The
`<pre class="mermaid">` blocks are rendered to SVG by mermaid.js inside Chromium.

## Title, headings, and TOC

- `_extract_front_matter_title()` looks for a `title:` line in YAML front-matter.
- Otherwise the title is the first H1's text, else the `fallback_title` (the
  input file stem, passed by `converter`).
- `_collect_headings()` walks the token stream pairing `heading_open` tokens with
  their `inline` text and reading the `id` the anchors plugin assigned.
- `_build_toc_html()` (only when `features.toc`) emits a `<nav class="toc">` with
  indented links for H1–H3. Note the TOC title is the literal string `目錄`
  (Chinese for "Contents") — change here if you need it localized/configurable.

The heading anchors serve double duty: in-document TOC links **and** the source
for the PDF bookmark outline that Chromium generates.

## Output contract

`render_markdown()` returns a `RenderedDoc`. Its `.html` is a **fragment** (no
`<html>`/`<head>`/`<body>`). The full document is assembled later by
`html_template.build_html()`. Keep presentation/`<head>` concerns out of this
module.
