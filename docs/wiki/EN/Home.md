# md-to-pdf-cli — Developer Wiki

`md-to-pdf-cli` converts a local Markdown file into a PDF using **headless
Chromium** as the rendering engine. The package is published on PyPI as
`md-to-pdf-cli`, but the import package and the CLI command are both `md2pdf`.

This wiki is for the project's *developers* (you, future-you, and contributors).
It explains how the code is organized, why the key decisions were made, and
where to look when you need to change something. For *usage* instructions, see
the top-level [`README.md`](../../../README.md).

## Why this tool exists

It was built to fix concrete fidelity bugs that other Markdown→PDF tools hit:

- **Garbled CJK / Chinese text (mojibake)** — fixed by reading source as
  `utf-8-sig` and shipping a CJK-first font stack.
- **Tables truncated across page breaks** — fixed with paged-media CSS
  (`thead { display: table-header-group }`, `break-inside: avoid`).
- **Broken images after conversion** (that looked fine in the editor preview) —
  fixed by loading the page from a real `file://` document so Chromium will load
  local image subresources.

Chromium was chosen deliberately: it is the same engine most Markdown editors
use for their preview, so "looks right in preview, breaks in PDF" issues
largely disappear, and code highlighting / math / mermaid all work natively
without a second pre-render step.

## The pipeline at a glance

```
.md file
  │  read_markdown()  ── utf-8-sig (strips BOM → fixes CJK mojibake)
  ▼
render_markdown()    ── markdown-it-py + plugins; Pygments highlight (server-side)
  │  HTML body fragment + title + headings + optional TOC
  ▼
rewrite_image_sources()  ── relative <img src> → absolute file:// or data URI
  ▼
build_html()         ── Jinja2 template; inline ALL assets (CSS, KaTeX+fonts, mermaid)
  │  one self-contained HTML string
  ▼
render_pdf()         ── Chromium: goto(temp file://) → wait for __md2pdf_ready → page.pdf()
  ▼
.pdf file
```

`converter.convert()` is the orchestrator that wires these five stages together
([converter.py](PDF-Rendering.md) calls them in order).

## Module map

| Module | Responsibility | Wiki page |
|--------|----------------|-----------|
| `cli.py` | Typer CLI, default-command shorthand, flag overrides, `init` | [CLI](CLI.md) |
| `config.py` | Dataclass schema, TOML loading, precedence rules | [Configuration](Configuration.md) |
| `converter.py` | Orchestrates md → html → pdf | [Architecture](Architecture.md) |
| `markdown_render.py` | Markdown → HTML, Pygments highlight, math, mermaid, TOC | [Markdown Rendering](Markdown-Rendering.md) |
| `images.py` | Rewrite `<img src>` to resolve/embed at print time | [Images](Images.md) |
| `html_template.py` | Assemble a single self-contained HTML doc | [HTML & Assets](HTML-and-Assets.md) |
| `pdf_render.py` | Drive Chromium, wait for render, emit PDF | [PDF Rendering](PDF-Rendering.md) |
| `assets/` | Template, default theme CSS, vendored KaTeX + mermaid | [HTML & Assets](HTML-and-Assets.md) |

## Where to start reading

- New to the codebase? Read [Architecture](Architecture.md) first, then follow
  the pipeline page by page.
- Changing CLI behavior or flags? → [CLI](CLI.md) + [Configuration](Configuration.md).
- A rendering bug (math/mermaid/code/tables)? → [Markdown Rendering](Markdown-Rendering.md)
  and [HTML & Assets](HTML-and-Assets.md).
- A "blank PDF / image broken / hangs" bug? → [PDF Rendering](PDF-Rendering.md).
- Setting up your environment or running tests? → [Development](Development.md).

## Project facts

- **Python**: 3.12+ (uses stdlib `tomllib`).
- **Package manager**: [`uv`](Development.md) for everything — deps, running,
  building, publishing. Do not use `pip`/`venv` directly in this repo.
- **Runtime deps**: `markdown-it-py`, `mdit-py-plugins`, `pygments`, `jinja2`,
  `playwright`, `typer`.
- **Chromium is not a pip dependency** — it is a browser binary Playwright
  downloads once (`playwright install chromium`) into a shared cache.
- **License**: MIT.
