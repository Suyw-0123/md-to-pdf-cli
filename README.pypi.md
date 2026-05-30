# md-to-pdf-cli

Convert local Markdown files to **PDF** using headless Chromium — the same engine
your editor preview uses, so what you see is what you get.

- 📦 **Source & full docs:** https://github.com/Suyw-0123/md-to-pdf-cli
- 📖 **Developer wiki:** https://github.com/Suyw-0123/md-to-pdf-cli/tree/main/docs/wiki

The CLI command is `md2pdf` (the PyPI package is `md-to-pdf-cli`).

## Install

Requires Python 3.12+.

```bash
# with uv (recommended): installs the `md2pdf` command, isolated
uv tool install md-to-pdf-cli
uv tool run --from md-to-pdf-cli playwright install chromium   # one-time browser download

# or with pip
pip install md-to-pdf-cli
playwright install chromium                                    # one-time browser download
```

Chromium is **not** a pip dependency — it's a browser binary Playwright downloads
once into a shared cache. If it's missing, `md2pdf` tells you the exact command to run.

## Quick start

```bash
md2pdf report.md                 # writes report.pdf next to the input
md2pdf report.md -o out/doc.pdf  # choose the output path
md2pdf init                      # scaffold md2pdf.toml + theme.css
```

`md2pdf <file>` is shorthand for `md2pdf convert <file>`. Run `md2pdf --help` for
all options.


## Configuration

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
```

See the full **[README](https://github.com/Suyw-0123/md-to-pdf-cli#readme)** and
**[wiki](https://github.com/Suyw-0123/md-to-pdf-cli/tree/main/docs/wiki)** on GitHub
for the complete options table, theming guide, troubleshooting, and architecture.

## License

MIT
