# Configuration (`config.py`)

Configuration is a set of frozen-ish dataclasses loaded from a `md2pdf.toml`
file (via stdlib `tomllib`), with built-in defaults and CLI overrides layered on
top.

## Precedence

```
CLI flags  >  md2pdf.toml  >  built-in dataclass defaults
```

`config.py` owns the bottom two layers (defaults + file). The CLI layer
(`cli.py`'s `_apply_overrides`) applies the top layer. `load_config()` never sees
CLI flags — keep that separation.

## Loading

- `find_config_file(explicit, start)` (config.py:168): an explicit `--config`
  path wins (and raises `FileNotFoundError` if missing); otherwise it looks for
  `md2pdf.toml` in the CWD. No config file found → built-in defaults.
- `load_config()` (config.py:178): reads the TOML and builds `Config` via
  `Config.from_dict(data, base_dir=...)`. `base_dir` is the **config file's
  directory** and is used to resolve relative CSS paths.

## The schema

All sections are optional; each dataclass has a `from_dict` classmethod that
fills missing keys from defaults and coerces types defensively.

### `[output]` → `OutputConfig`

| Key | Default | Notes |
|-----|---------|-------|
| `page_size` | `"A4"` | Passed to Chromium as `format`. `A4`, `Letter`, `Legal`, … |
| `landscape` | `false` | Orientation. |
| `margin` | `2cm / 2cm / 1.8cm / 1.8cm` | `Margin` dataclass; inline TOML table. |

`Margin.as_playwright()` returns the dict shape `page.pdf()` expects.

### `[theme]` → `ThemeConfig`

| Key | Default | Notes |
|-----|---------|-------|
| `base` | `"default"` | Reserved for future named themes. |
| `css` | `[]` | Extra CSS files, appended after the default theme (later wins). A bare string is accepted and wrapped into a list. |
| `font_family` | `DEFAULT_FONT_FAMILY` | CSS font stack; CJK faces first. |
| `code_style` | `"default"` | Any Pygments style name. |

`DEFAULT_FONT_FAMILY` (config.py:16) lists `Noto Sans CJK TC/SC`, `Microsoft
JhengHei`, `PingFang TC`, etc. *first* so CJK text renders with a real CJK font
instead of tofu. This is part of the CJK-correctness story.

### `[features]` → `FeaturesConfig`

| Key | Default | Effect |
|-----|---------|--------|
| `math` | `true` | Enable dollarmath parsing + KaTeX injection. |
| `mermaid` | `true` | Inject mermaid runtime + render `pre.mermaid`. |
| `toc` | `false` | Build a table-of-contents page. |
| `embed_images` | `false` | Inline local images as base64 data URIs. |

### `[header]` / `[footer]` → `BannerConfig`

`enabled` + `template` (inner HTML). The **footer defaults to enabled** with a
centered `current / total` page-number template; the header defaults to off. The
template may use Chromium's placeholder classes: `title`, `date`, `url`,
`pageNumber`, `totalPages`. See [PDF Rendering](PDF-Rendering.md) for how these
are wrapped and rendered.

## CSS path resolution

`Config.resolved_css_paths()` (config.py:159) turns each `theme.css` entry into
an absolute path: absolute paths pass through; relative paths resolve against
`base_dir` (the config file's directory). **Exception:** CSS added via the CLI
`--css` flag is pre-resolved against the CWD in `cli.py` before being appended,
because at that point there may be no config file to anchor against.

## Adding a new setting (checklist)

1. Add the field (with a default) to the right dataclass.
2. Read + coerce it in that dataclass's `from_dict`.
3. If user-facing on the CLI, add a Typer `Option` in `cli.py` and a branch in
   `_apply_overrides`.
4. If it changes rendering, thread it into the relevant stage (`markdown_render`,
   `html_template`, or `pdf_render`).
5. Add it to `_SAMPLE_TOML` in `cli.py` and document it in the README.
6. Add/extend a test in `tests/test_config.py`.
