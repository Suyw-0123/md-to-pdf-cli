# Architecture

This page explains the overall design and the orchestration glue. Each stage has
its own deep-dive page; this is the map that ties them together.

## Design principles

1. **One self-contained HTML string.** Everything the browser needs — theme CSS,
   Pygments CSS, KaTeX (including fonts as data URIs), mermaid — is inlined into a
   single HTML document. Conversion is fully offline and reproducible; there are
   no CDN fetches and no external stylesheet/font requests.
2. **Server-side where deterministic, browser-side where necessary.** Code
   highlighting is done by Pygments in Python (deterministic, no browser
   variance). Math (KaTeX) and diagrams (mermaid) need a JS runtime, so they run
   in Chromium, and we *wait* for them to finish before printing.
3. **Resolve paths relative to the Markdown file, not the CWD.** Images and the
   like are resolved against the source `.md` directory so conversion works from
   anywhere.
4. **Clear precedence:** CLI flags > config file > built-in defaults.

## The orchestrator: `converter.convert()`

`src/md2pdf/converter.py` is intentionally tiny — it is the single place that
shows the whole flow:

```python
def convert(input_path, output_path, config) -> ConversionResult:
    source = read_markdown(input_path)                       # 1. read (utf-8-sig)
    doc = render_markdown(source, config.features, ...)      # 2. md -> html body
    doc.html = rewrite_image_sources(doc.html, md_dir, ...)  # 3. fix image srcs
    html = build_html(doc, config)                           # 4. assemble HTML
    render_pdf(html, out, config)                            # 5. Chromium -> PDF
    return ConversionResult(...)
```

If you are tracing a bug, find which of these five calls owns the symptom and
jump to that module's wiki page.

### Stage 1 — `read_markdown()`

Reads the file with `encoding="utf-8-sig"`. The `-sig` variant transparently
strips a UTF-8 BOM if present. This is the fix for the **garbled-Chinese bug**:
a leaked BOM or mis-detected encoding was corrupting the first characters.

### Stage 2 — `render_markdown()`

Markdown → HTML *body fragment* (not a full document) plus metadata: the
document `title` (from front-matter `title:` or the first H1), the list of
`headings`, and an optional TOC. See [Markdown Rendering](Markdown-Rendering.md).

### Stage 3 — `rewrite_image_sources()`

Rewrites every `<img src>` so it resolves at print time: relative paths become
absolute `file://` URLs (or base64 data URIs when `embed_images` is on). See
[Images](Images.md).

### Stage 4 — `build_html()`

Renders the Jinja2 template, inlining all CSS/JS/font assets, producing the
single HTML string. See [HTML & Assets](HTML-and-Assets.md).

### Stage 5 — `render_pdf()`

Launches Chromium, navigates to a temp `file://` copy of the HTML, waits for the
`window.__md2pdf_ready` flag, then calls `page.pdf()`. See
[PDF Rendering](PDF-Rendering.md).

## Data objects that flow through

- **`Config`** (`config.py`) — the fully merged configuration. Built once in the
  CLI layer and threaded through every stage.
- **`RenderedDoc`** (`markdown_render.py`) — `html`, `title`, `headings`,
  `toc_html`. Note `html` is mutated in place at stage 3.
- **`ConversionResult`** (`converter.py`) — `input_path`, `output_path`,
  `title`; returned to the CLI for the success message.

## Why a body fragment, not a full HTML document, from stage 2

Keeping the Markdown renderer's output as a *fragment* means there is exactly one
place (`html_template.py`) that owns the `<head>`, asset inlining, language
attribute, TOC placement, and the readiness script. The renderer stays focused
on content; the template owns presentation and the browser contract.

## Failure handling

The CLI (`cli.py`) catches three classes of error and turns them into clean,
colored messages with exit code 1:

- `BrowserNotInstalledError` — Chromium missing; printed in yellow with the
  install hint.
- `FileNotFoundError` — bad input or `--config` path.
- Any other `Exception` — surfaced as `Conversion failed: …` rather than a
  traceback.
