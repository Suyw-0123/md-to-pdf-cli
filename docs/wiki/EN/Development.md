# Development

Everything in this repo is driven by [`uv`](https://docs.astral.sh/uv/). Do not
use `pip`/`python -m venv` directly here — `python3 -m venv` even fails on the
maintainer's box (no `ensurepip`); use `uv venv` if you need a raw env.

## Setup

```bash
uv sync                              # install runtime + dev deps from uv.lock
uv run playwright install chromium   # one-time browser download (shared cache)
```

## Running locally

```bash
uv run md2pdf tests/fixtures/sample.md -o /tmp/sample.pdf
uv run md2pdf --help
```

## Tests

```bash
uv run pytest                 # full suite (the end-to-end test launches Chromium)
uv run pytest -m "not slow"   # skip the browser-based test (fast, no Chromium)
```

Test layout (`tests/`):

| File | Covers |
|------|--------|
| `test_config.py` | TOML loading, defaults, precedence, CSS path resolution |
| `test_markdown_render.py` | highlight wrapping, math delimiters, mermaid passthrough, TOC/title |
| `test_images.py` | `<img src>` rewriting, remote skip, missing-file passthrough, data URIs |
| `test_converter.py` | end-to-end `.md → .pdf` (marked `slow`); incl. the relative-parent-image regression |
| `fixtures/sample.md`, `fixtures/logo.png` | a document exercising CJK, tables, images, mermaid, math, code |

The `slow` marker is declared in `pyproject.toml` (`[tool.pytest.ini_options]`)
and is the convention for any test that launches Chromium.

> When asserting on PDF text extracted with `pypdf`, remember CJK glyphs can come
> back with extra spacing between characters — normalize whitespace before
> comparing, or the assertion will be flaky.

## Lint & format

```bash
uv run ruff check .
uv run ruff format --check .
```

Ruff config (`pyproject.toml`): line length 100, target `py312`, rules
`E,F,I,UP,B,W`. Two ignores, both deliberate:

- **`E501`** — some Typer option declarations and wrapped strings are clearer
  past 100 cols.
- **`B008`** — Typer *requires* `typer.Option(...)`/`Argument(...)` calls in
  parameter defaults.

Where B904 ("raise from") applies, use `raise typer.Exit(code=1) from exc`.

## CI / CD

- **CI** (`.github/workflows/ci.yml`): on push/PR, `uv sync --locked`, then
  `ruff check` + `ruff format --check`. Pinned actions: `actions/checkout@v6`,
  `astral-sh/setup-uv@v8.1.0` (avoid the moving `@v8` tag — it failed to resolve).
- **Publish** (`.github/workflows/publish.yml`): on a published GitHub Release
  (or manual dispatch), `uv build` + `uv publish` via **PyPI Trusted Publishing
  (OIDC)** — no token. Needs `permissions: id-token: write`. Uses
  `--check-url https://pypi.org/simple/md-to-pdf-cli/` so re-runs skip
  already-uploaded files instead of failing.
- **Docker** (`.github/workflows/docker.yml`): same triggers as Publish. Builds
  the `Dockerfile` and pushes to `ghcr.io/${{ github.repository }}` (i.e.
  `ghcr.io/suyw-0123/md-to-pdf-cli`). Tags come from `docker/metadata-action`
  (`{{version}}`, `{{major}}.{{minor}}`, and `latest` on the default branch).
  Needs `permissions: packages: write`; auth is the built-in `GITHUB_TOKEN`, no
  secret to manage. The first pushed image is private — make it public once under
  the repo's *Packages* settings if you want anonymous `docker pull`.

## Docker image

`Dockerfile` builds a self-contained image: `python:3.12-slim` + CJK fonts
(`fonts-noto-cjk`) + the CLI installed with `pip install .` + `playwright install
--with-deps chromium`. The browser is baked in at `PLAYWRIGHT_BROWSERS_PATH=/opt/playwright`
(world-readable). The image sets two md2pdf env vars: `MD2PDF_AUTO_INSTALL_BROWSER=0`
(don't download at runtime — it's already here) and `MD2PDF_CHROMIUM_NO_SANDBOX=1`
(launch Chromium with `--no-sandbox --disable-dev-shm-usage`, required in most
containers — see [PDF Rendering](PDF-Rendering.md)). `ENTRYPOINT ["md2pdf"]` with
`WORKDIR /work`, so `docker run -v "$PWD:/work" <image> report.md` converts a
mounted file. Build/run locally:

```bash
docker build -t md2pdf .
docker run --rm -v "$PWD:/work" md2pdf tests/fixtures/sample.md
```

## Release flow

1. Bump `version` in **both** `pyproject.toml` and `src/md2pdf/__init__.py`.
2. Commit & push.
3. Create a `vX.Y.Z` GitHub Release → the publish workflow uploads to PyPI.

PyPI trusted-publisher config must match the repo: owner `Suyw-0123`, repo
`md-to-pdf-cli`, workflow `publish.yml`, environment blank.

### Packaging notes

- Backend is `uv_build`; `[tool.uv.build-backend] module-name = "md2pdf"` maps the
  distribution name `md-to-pdf-cli` to the import package `md2pdf`.
- `uv build` bundles everything under `src/md2pdf/assets/` (KaTeX + fonts,
  mermaid, template, CSS) into the wheel automatically — no manifest needed.
- Production PyPI has a **name-similarity filter** (TestPyPI does not); that is
  why the name is `md-to-pdf-cli` and not `markdown-to-pdf`.
- The author email `su.willie.gm@gmail.com` in `pyproject.toml` is intentional —
  do not "fix" it.

## Adding a feature: where things live

| You want to… | Touch |
|--------------|-------|
| add a CLI flag | `cli.py` (`Option` + `_apply_overrides`) |
| add a config setting | `config.py` (dataclass + `from_dict`) + `_SAMPLE_TOML` |
| change Markdown parsing | `markdown_render.py` (`build_parser` / plugins) |
| change page styling | `assets/default.css` (or document a `--md2pdf-*` var) |
| change the HTML shell / readiness | `assets/template.html.j2` + `html_template.py` |
| change PDF/page options | `pdf_render.py` (`pdf_kwargs`) |
| fix image resolution | `images.py` |
