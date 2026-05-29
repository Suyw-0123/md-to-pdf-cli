# md2pdf

Convert local Markdown files to **PDF** via headless Chromium — the same engine
your editor preview uses, so what you see is what you get.

Built to fix the things other converters get wrong:

- **Chinese / CJK** text renders correctly (UTF-8 + BOM handling, CJK font stack) — no mojibake.
- **Tables don't get sliced** across pages; the header row repeats on each page.
- **Images don't break** — relative paths resolve against the source file, or can be embedded as data URIs.
- **mermaid diagrams**, **LaTeX math** (KaTeX), and **syntax-highlighted code** (Pygments) all render.
- Full control over styling via **CSS themes** and a **TOML config file**, plus page headers/footers and page numbers.

## Install

Requires Python 3.12+. The package is published on PyPI as **`markdown-to-pdf`**;
the command and import package are both `md2pdf`.

### As a user

```bash
# with uv (installs the `md2pdf` command globally, isolated)
uv tool install markdown-to-pdf
uv tool run --from markdown-to-pdf playwright install chromium   # one-time browser download

# or with pip
pip install markdown-to-pdf
playwright install chromium                                      # one-time browser download
```

> **Why the extra browser step?** md2pdf renders through headless Chromium
> (via Playwright). Chromium is **not** a pip dependency — it's a ~120 MB
> browser binary downloaded once into a shared cache (`~/.cache/ms-playwright`).
> If you skip it, md2pdf prints the exact command to run.

### From source (development)

```bash
uv sync
uv run playwright install chromium
```

## Usage

```bash
# Simplest: PDF written next to the input
uv run md2pdf report.md

# Choose output path
uv run md2pdf report.md -o out/report.pdf

# Common options
uv run md2pdf report.md --page-size Letter --margin 1.5cm --code-style monokai --toc
uv run md2pdf report.md --css custom.css --no-mermaid
```

`md2pdf <file>` is shorthand for `md2pdf convert <file>`.

### Config file

Scaffold a starter config and theme:

```bash
uv run md2pdf init
```

This writes `md2pdf.toml` and `theme.css`. `md2pdf` auto-loads `md2pdf.toml`
from the current directory (override with `-c path/to/config.toml`). CLI flags
override the config file, which overrides built-in defaults.

```toml
[output]
page_size = "A4"
margin = { top = "2cm", bottom = "2cm", left = "1.8cm", right = "1.8cm" }

[theme]
css = ["theme.css"]
code_style = "default"           # any Pygments style
# font_family = '"Noto Sans CJK TC", "Microsoft JhengHei", sans-serif'

[features]
math = true
mermaid = true
toc = false
embed_images = false             # inline images for a self-contained PDF

[footer]
enabled = true
template = '<span class="pageNumber"></span> / <span class="totalPages"></span>'

[header]
enabled = false
template = '<span class="title"></span>'
```

Header/footer templates may use these Chromium placeholders: `pageNumber`,
`totalPages`, `title`, `date`, `url`.

## How it works

```
.md ──▶ markdown-it-py (+ Pygments, dollarmath) ──▶ self-contained HTML
     ──▶ Chromium (KaTeX + mermaid render, fonts load) ──▶ page.pdf() ──▶ .pdf
```

All assets (theme CSS, Pygments CSS, KaTeX with fonts, mermaid) are inlined, so
conversion works fully offline and reproducibly.

## Development

```bash
uv run pytest                 # full suite (the end-to-end test launches Chromium)
uv run pytest -m "not slow"   # skip the browser-based end-to-end test
```

## Troubleshooting

- **`Chromium is not installed for Playwright`** — run `playwright install chromium`
  (or `uv tool run --from markdown-to-pdf playwright install chromium` for a uv-tool install).
- **Images show as broken** — md2pdf resolves relative image paths against the
  Markdown file's directory; make sure the paths are correct relative to the
  `.md` file. Remote `http(s)` images are fetched at render time.

## License

MIT
