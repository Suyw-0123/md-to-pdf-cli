# HTML & Assets (`html_template.py`, `assets/`)

This stage assembles the Markdown body fragment + config into **one
self-contained HTML document**. "Self-contained" is the whole point: every
stylesheet, script, and font is inlined, so the page renders identically from
any origin and conversion never touches the network.

## `build_html(doc, config)` (html_template.py:57)

It reads assets, builds a context dict, and renders the Jinja2 template:

| Context key | Source |
|-------------|--------|
| `body` | `doc.html` (the rendered fragment) |
| `title`, `toc_html` | from `RenderedDoc` |
| `theme_css` | `assets/default.css` |
| `extra_css` | concatenated user CSS from `config.resolved_css_paths()` |
| `pygments_css` | `pygments_css(config.theme.code_style)` |
| `font_family` | `config.theme.font_family`, injected as `--md2pdf-font` |
| `katex_css` / `katex_js` / `katex_autorender_js` | only when `features.math` |
| `mermaid_js` | only when `features.mermaid` |

Asset files are read from the installed package via
`importlib.resources.files("md2pdf") / "assets"` (html_template.py:21) — never via
filesystem-relative paths — so it works the same when installed as a wheel.

## The template (`assets/template.html.j2`)

A minimal HTML5 document. Order matters in `<head>`:

1. KaTeX CSS (if math) → 2. Pygments CSS → 3. theme CSS → 4. the
`--md2pdf-font` variable → 5. user extra CSS **last** (so it overrides
everything).

`<body>` contains the optional TOC `<nav>` then `<main class="md2pdf-content">`
with the body. At the end, scripts for KaTeX and mermaid (each gated by its
feature flag) and the **readiness script**.

### The readiness contract: `window.__md2pdf_ready`

This is the linchpin that prevents "printed too early / half-drawn" PDFs. An
async IIFE:

1. runs KaTeX auto-render over `document.body` (delimiters: `\[ \]`, `\( \)`,
   `$$`, `$`; `throwOnError: false`),
2. initializes mermaid (`startOnLoad: false`, `securityLevel: "loose"`) and
   `await`s `mermaid.run()` over all `pre.mermaid` nodes,
3. `await`s `document.fonts.ready`,
4. sets `window.__md2pdf_ready = true`.

`pdf_render.py` waits on exactly this flag before calling `page.pdf()`. If you
add another async render step, do it **before** the flag is set, or the PDF may
capture an unfinished page. See [PDF Rendering](PDF-Rendering.md).

## Inlining KaTeX fonts as data URIs

`_katex_css_inlined()` (html_template.py:34) reads `katex.min.css` and rewrites
every `url(fonts/Foo.woff2)` into a base64 `data:font/woff2` URI via the
`_FONT_URL` regex. Without this, KaTeX glyphs would be invisible: the page has no
base URL that resolves `fonts/…`, and Chromium would block those subresources.
Only `.woff2` is vendored (every modern Chromium supports it), keeping the bundle
small. The result is `lru_cache`d since it is identical every run.

## `assets/default.css` — the paged-media theme

This stylesheet encodes most of the "fidelity fixes". Highlights:

- **Tables across pages:** `thead { display: table-header-group }` repeats the
  header row on each page; `tr, td, th { break-inside: avoid }` stops rows being
  sliced. This fixes the **table-truncation bug**.
- **Images:** `max-width: 100%`, `height: auto`, `break-inside: avoid` — never
  overflow the page, never split.
- **Headings:** `break-after: avoid` so a heading never gets orphaned at the
  bottom of a page.
- **Code:** `pre.highlight` styling with `white-space: pre-wrap` + `word-break`
  so long lines wrap instead of overflowing; the `.highlight` selector is where
  the Pygments CSS lands.
- **CJK:** `--md2pdf-font` (config-driven, CJK-first) and a CJK-aware monospace
  stack (`--md2pdf-mono`).
- **TOC:** `nav.toc { break-after: page }` so the contents sit on their own page.
- `-webkit-print-color-adjust: exact` so backgrounds/colors actually print.

CSS custom properties (`--md2pdf-*`) are the supported extension surface: a user
`theme.css` (or `--css`) loaded last can override any of them without replacing
the whole sheet.

## Vendored assets

Under `assets/vendor/`:

- **KaTeX** (`katex.min.css`, `katex.min.js`, `contrib/auto-render.min.js`, and
  `fonts/*.woff2`).
- **mermaid** (`mermaid.min.js`) — sets `globalThis.mermaid`.

These are pinned, offline copies. To upgrade, replace the files (keep the woff2
font set complete for KaTeX) and re-run the end-to-end test to confirm rendering
still completes and `__md2pdf_ready` is reached.

## Trusted-HTML note

The Jinja2 `Environment` uses `autoescape=False` (html_template.py:53) **on
purpose**: body, CSS, and JS are all pre-escaped/trusted content we generate, and
auto-escaping them would corrupt the inlined scripts and styles. Do not feed
untrusted strings directly into the template context.
