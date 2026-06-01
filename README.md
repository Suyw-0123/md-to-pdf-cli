# md-to-pdf-cli

Convert local Markdown files to **PDF** using headless Chromium

![installation](installation.png)

## Install

Requires Python 3.12+.

```bash
# with uv (recommended): installs the `md2pdf` command, isolated
uv tool install md-to-pdf-cli

# or with pip
pip install md-to-pdf-cli
```

That's it. Chromium is **not** a pip dependency — it's a browser binary Playwright
downloads once into a shared cache. The first time you run `md2pdf` it detects the
missing browser and downloads it automatically (~150 MB, one time only).

Prefer to do it up front, or running in CI? Trigger the download yourself:

```bash
playwright install chromium                                    # pip install
uv tool run --from md-to-pdf-cli playwright install chromium   # uv tool install
```

To disable the automatic first-run download (e.g. in CI), set
`MD2PDF_AUTO_INSTALL_BROWSER=0`.

## Run with Docker

No Python, no Chromium, no fonts to install — the image ships the CLI, headless
Chromium, **and** CJK fonts. Mount your folder at `/work` and the PDF lands next
to the input:

```bash
docker run --rm -v "$PWD:/work" ghcr.io/suyw-0123/md-to-pdf-cli report.md
docker run --rm -v "$PWD:/work" ghcr.io/suyw-0123/md-to-pdf-cli report.md -o out/doc.pdf
docker run --rm -v "$PWD:/work" ghcr.io/suyw-0123/md-to-pdf-cli init   # scaffold config
```

The entrypoint is `md2pdf`, so everything after the image name is passed straight
to the CLI (`--help` works too). Pin a version with a tag, e.g.
`ghcr.io/suyw-0123/md-to-pdf-cli:0.1`.

By default the output PDF is owned by `root` (the container user). To have it owned
by you, add `--user "$(id -u):$(id -g)"`:

```bash
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD:/work" ghcr.io/suyw-0123/md-to-pdf-cli report.md
```

Build it yourself instead of pulling:

```bash
docker build -t md2pdf .
docker run --rm -v "$PWD:/work" md2pdf report.md
```

> **TODO**: Automatically download Chromium on the first run to remove this manual step.

## Quick start

```bash
md2pdf report.md                 # writes report.pdf next to the input
md2pdf report.md -o out/doc.pdf  # choose the output path
```

`md2pdf <file>` is shorthand for `md2pdf convert <file>`.

## Usage

```
md2pdf <input.md> [OPTIONS]
```

| Option | What it does |
|--------|--------------|
| `-o, --output PATH` | Output PDF path (default: same name as input). |
| `-c, --config PATH` | Use a specific `md2pdf.toml` (default: auto-load from current dir). |
| `--page-size NAME` | `A4`, `Letter`, `Legal`, … |
| `--margin SIZE` | Margin on all sides, e.g. `2cm`. |
| `--landscape / --portrait` | Page orientation. |
| `--css FILE` | Extra CSS file, applied after the theme (repeatable). |
| `--code-style NAME` | Pygments highlight style, e.g. `monokai`. |
| `--font STACK` | CSS `font-family` stack. |
| `--toc / --no-toc` | Generate a table of contents page. |
| `--math / --no-math` | LaTeX math rendering. |
| `--mermaid / --no-mermaid` | mermaid diagram rendering. |
| `--embed-images / --no-embed-images` | Inline local images as data URIs. |
| `--header HTML`, `--footer HTML` | Page header/footer (see [Headers & page numbers](#headers-footers--page-numbers)). |

Run `md2pdf --help` for the full list.

## What it renders, and how to use it

Write standard Markdown — these capabilities work out of the box.

### Code blocks

Fenced code blocks are highlighted server-side with Pygments. Just tag the language:

````markdown
```python
def greet(name): return f"Hello, {name}"
```
````

Pick the colour scheme with `--code-style monokai` (any Pygments style name).

### Math

Inline `$...$` and block `$$...$$` LaTeX are typeset with KaTeX:

```markdown
Euler's identity is $e^{i\pi} + 1 = 0$.

$$
\int_{-\infty}^{\infty} e^{-x^2}\,dx = \sqrt{\pi}
$$
```

### Diagrams

A ```` ```mermaid ```` fence is rendered to a vector diagram:

````markdown
```mermaid
flowchart LR
    A[Markdown] --> B[md2pdf] --> C[(PDF)]
```
````

### Tables

GFM tables are supported. Long tables that span pages are not sliced mid-row, and
the header row repeats at the top of each page.

### Images

Relative image paths are resolved against the **Markdown file's** location, so
`![](../figures/plot.png)` works regardless of where you run the command. Remote
`http(s)` images are fetched at render time. Use `--embed-images` to inline local
images into a fully self-contained PDF.

### Chinese / CJK

CJK text renders correctly (UTF-8 with BOM handling and a CJK-first font stack).
On Linux, install CJK fonts first — see [Troubleshooting](#troubleshooting).

### Table of contents & bookmarks

`--toc` adds a contents page built from your headings. The PDF also gets an
outline (bookmarks) from the heading structure automatically.

### Headers, footers & page numbers

Enabled via the config file (below). Templates may use Chromium's placeholders:
`pageNumber`, `totalPages`, `title`, `date`, `url`. A centered "page / total"
footer is on by default.

## Configuration

Scaffold a config and a starter theme:

```bash
md2pdf init        # writes md2pdf.toml and theme.css
```

`md2pdf` auto-loads `md2pdf.toml` from the current directory. Precedence:
**CLI flags > config file > defaults.**

```toml
[output]
page_size = "A4"
margin = { top = "2cm", bottom = "2cm", left = "1.8cm", right = "1.8cm" }

[theme]
css = ["theme.css"]              # extra CSS, applied after the default theme
code_style = "default"           # any Pygments style
# font_family = '"Noto Sans CJK TC", "Microsoft JhengHei", sans-serif'

[features]
math = true
mermaid = true
toc = false
embed_images = false

[footer]
enabled = true
template = '<span class="pageNumber"></span> / <span class="totalPages"></span>'

[header]
enabled = false
template = '<span class="title"></span>'
```

Custom styling: anything in your `theme.css` (or `--css`) overrides the built-in
theme, including the `--md2pdf-*` CSS variables it defines.

## How it works

```
.md ──▶ markdown-it-py (+ Pygments, dollarmath) ──▶ self-contained HTML
     ──▶ Chromium (KaTeX + mermaid render, fonts load) ──▶ page.pdf() ──▶ .pdf
```

All assets (theme CSS, Pygments CSS, KaTeX with fonts, mermaid) are inlined into
the HTML, so conversion is offline and reproducible. md2pdf waits for math and
diagrams to finish rendering before printing, so nothing comes out half-drawn.

## Troubleshooting

- **Chromium auto-download failed** — md2pdf normally downloads Chromium on first
  run, but if that fails (no network, restricted environment, or you set
  `MD2PDF_AUTO_INSTALL_BROWSER=0`) install it manually with `playwright install
  chromium` (or `uv tool run --from md-to-pdf-cli playwright install chromium` for a
  uv-tool install).
- **Chinese/CJK text shows as boxes (tofu) on Linux** — install CJK fonts, e.g.
  `sudo apt install fonts-noto-cjk` on Debian/Ubuntu. Windows and macOS already
  ship with CJK fonts.
- **Chromium fails to launch on a headless Linux server** — install its system
  libraries: `playwright install-deps chromium` (needs root).

## Development

```bash
uv sync
uv run playwright install chromium
uv run pytest                 # full suite (the end-to-end test launches Chromium)
uv run pytest -m "not slow"   # skip the browser-based test
uv run ruff check . && uv run ruff format --check .
```

## License

MIT
