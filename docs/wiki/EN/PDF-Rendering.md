# PDF Rendering (`pdf_render.py`)

The final stage: drive headless Chromium via
[Playwright](https://playwright.dev/python/) to turn the self-contained HTML into
a PDF. This module is small but holds the two most important correctness
decisions in the project.

## `render_pdf(html, output_path, config)` (pdf_render.py:59)

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

### Critical decision #1 — load via a temp `file://` page, not `set_content()`

The obvious approach, `page.set_content(html)`, gives the page an `about:blank`
origin. Chromium then **refuses to load local `file://` images** ("Not allowed to
load local resource"), so every local image comes out blank — the broken-image
bug. A page served from a real `file://` URL *is* allowed to load `file://`
subresources. So we write the HTML to a temp file and `page.goto()` its
`file://` URI. This, together with [Images](Images.md) rewriting srcs to absolute
`file://`, is what makes local images work.

### Critical decision #2 — wait for `window.__md2pdf_ready`

`page.pdf()` is **not** called until `wait_for_function` confirms
`window.__md2pdf_ready === true`. That flag is set by the template's readiness
script only after KaTeX, mermaid, and font loading finish (see
[HTML & Assets](HTML-and-Assets.md)). Without this wait, the PDF would frequently
capture a page with un-typeset math or un-rendered diagrams. The timeout is
`_RENDER_TIMEOUT_MS = 30_000` (30s) — if rendering hangs past that,
`wait_for_function` raises and the CLI reports a clean failure.

`page.emulate_media(media="print")` ensures print CSS (`@page`, `print-color-
adjust`, etc.) is active before capture.

## `page.pdf()` options

`pdf_kwargs` (pdf_render.py:66) maps config to Playwright:

| Option | Value | Why |
|--------|-------|-----|
| `format` | `config.output.page_size` | A4/Letter/… |
| `landscape` | `config.output.landscape` | orientation |
| `margin` | `config.output.margin.as_playwright()` | per-side margins |
| `print_background` | `True` | print background colors/shading |
| `prefer_css_page_size` | `False` | the `format` above wins over any `@page size` |
| `tagged` | `True` | accessible/tagged PDF — **required** for the outline |
| `outline` | `True` | emit heading bookmarks |

> **Bookmarks gotcha:** `outline=True` alone produced an *empty* outline. Chromium
> only emits the heading outline for a **tagged** PDF, so `tagged=True` is also
> required. Keep both.

## Headers, footers & page numbers

Chromium does **not** support CSS running headers (`@page @top-center`). Page
furniture must go through `display_header_footer` + `header_template` /
`footer_template`. When `config.header.enabled or config.footer.enabled`:

- `_wrap_banner(inner)` (pdf_render.py:46) wraps the user's inner HTML in a
  `<div>` with an explicit `font-size:9px`, full width, padding, muted color, and
  centered text. **This explicit sizing is mandatory** — Chromium renders header/
  footer templates at a near-zero default font size, so an unwrapped template is
  effectively invisible.
- A disabled side still needs a placeholder (`_EMPTY_BANNER = "<span></span>"`),
  otherwise Chromium shows its own default (e.g. the URL/date).
- Templates use Chromium's placeholder classes: `pageNumber`, `totalPages`,
  `title`, `date`, `url`. The default footer is `pageNumber / totalPages`.

## Browser-not-installed handling

Chromium is not a pip dependency. `_launch_chromium()` (pdf_render.py:37) catches
the Playwright launch error and, when the message contains `Executable doesn't
exist` or `playwright install`, raises `BrowserNotInstalledError` carrying the
`_INSTALL_HINT` text. The CLI prints that hint in yellow instead of a raw
traceback. The hint uses the published package name, so the uv-tool variant reads
`uv tool run --from md-to-pdf-cli playwright install chromium`.

## Lifecycle

The browser is always closed in a `finally`, and the temp directory is cleaned up
by its context manager, so there are no leaked Chromium processes or temp files
even on failure.
