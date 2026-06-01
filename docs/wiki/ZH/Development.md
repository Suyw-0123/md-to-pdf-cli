# 開發

這個 repo 的一切都用 [`uv`](https://docs.astral.sh/uv/) 驅動。請不要在這裡直接用
`pip`／`python -m venv`——在維護者的機器上 `python3 -m venv` 甚至會失敗（沒有
`ensurepip`）；若你需要一個原始環境，請用 `uv venv`。

## 設定

```bash
uv sync                              # 從 uv.lock 安裝執行期 + 開發依賴
uv run playwright install chromium   # 一次性瀏覽器下載（共用快取）
```

## 本地執行

```bash
uv run md2pdf tests/fixtures/sample.md -o /tmp/sample.pdf
uv run md2pdf --help
```

## 測試

```bash
uv run pytest                 # 完整套件（端到端測試會啟動 Chromium）
uv run pytest -m "not slow"   # 跳過瀏覽器測試（快、不需 Chromium）
```

測試結構（`tests/`）：

| 檔案 | 涵蓋 |
|------|------|
| `test_config.py` | TOML 載入、預設、優先序、CSS 路徑解析 |
| `test_markdown_render.py` | 高亮包裹、數學分隔符、mermaid 原樣輸出、TOC／標題 |
| `test_images.py` | `<img src>` 改寫、遠端跳過、缺檔原樣保留、data URI |
| `test_converter.py` | 端到端 `.md → .pdf`（標記 `slow`）；含相對父層圖片回歸 |
| `fixtures/sample.md`、`fixtures/logo.png` | 一份操練 CJK、表格、圖片、mermaid、數學、程式碼的文件 |

`slow` 標記宣告在 `pyproject.toml`（`[tool.pytest.ini_options]`），是任何會啟動 Chromium
之測試的慣例。

> 用 `pypdf` 抽出 PDF 文字來斷言時，記得 CJK 字符可能回來時字元間有額外空白——比較前先
> 正規化空白，否則斷言會很脆。

## Lint 與格式化

```bash
uv run ruff check .
uv run ruff format --check .
```

Ruff 設定（`pyproject.toml`）：line length 100、target `py312`、規則 `E,F,I,UP,B,W`。
兩個 ignore，都是刻意的：

- **`E501`**——某些 Typer option 宣告與換行字串超過 100 欄反而更清楚。
- **`B008`**——Typer *要求*在參數預設值裡呼叫 `typer.Option(...)`／`Argument(...)`。

凡是 B904（「raise from」）適用之處，用 `raise typer.Exit(code=1) from exc`。

## CI / CD

- **CI**（`.github/workflows/ci.yml`）：push/PR 時，`uv sync --locked`，再
  `ruff check` + `ruff format --check`。釘版 action：`actions/checkout@v6`、
  `astral-sh/setup-uv@v8.1.0`（避免會移動的 `@v8` tag——它曾無法解析）。
- **Publish**（`.github/workflows/publish.yml`）：在發布 GitHub Release（或手動 dispatch）
  時，透過 **PyPI Trusted Publishing（OIDC）** 做 `uv build` + `uv publish`——免 token。
  需要 `permissions: id-token: write`。使用
  `--check-url https://pypi.org/simple/md-to-pdf-cli/`，讓重跑時跳過已上傳的檔案而非失敗。
- **Docker**（`.github/workflows/docker.yml`）：觸發條件同 Publish。建置 `Dockerfile` 並推到
  `ghcr.io/${{ github.repository }}`（即 `ghcr.io/suyw-0123/md-to-pdf-cli`）。tag 由
  `docker/metadata-action` 產生（`{{version}}`、`{{major}}.{{minor}}`，預設分支再加 `latest`）。
  需要 `permissions: packages: write`；認證用內建的 `GITHUB_TOKEN`，免管理 secret。首次推出的
  image 是 private——若要讓匿名 `docker pull`，到 repo 的 *Packages* 設定改為 public。

## Docker image

`Dockerfile` 建一個自帶一切的 image：`python:3.12-slim` + CJK 字型（`fonts-noto-cjk`）+
用 `pip install .` 裝好 CLI + `playwright install --with-deps chromium`。瀏覽器在建置時就烤進
`PLAYWRIGHT_BROWSERS_PATH=/opt/playwright`（全域可讀）。image 設了兩個 md2pdf 環境變數：
`MD2PDF_AUTO_INSTALL_BROWSER=0`（不要在執行期下載——已經在裡面）與
`MD2PDF_CHROMIUM_NO_SANDBOX=1`（以 `--no-sandbox --disable-dev-shm-usage` 啟動 Chromium，
多數容器內必需——見 [PDF Rendering](PDF-Rendering.md)）。`ENTRYPOINT ["md2pdf"]` 搭配
`WORKDIR /work`，所以 `docker run -v "$PWD:/work" <image> report.md` 就能轉換掛載進來的檔案。
本機建置／執行：

```bash
docker build -t md2pdf .
docker run --rm -v "$PWD:/work" md2pdf tests/fixtures/sample.md
```

## 發布流程

1. 在 **`pyproject.toml` 與 `src/md2pdf/__init__.py` 兩處**同時 bump `version`。
2. Commit 並 push。
3. 建一個 `vX.Y.Z` GitHub Release → publish workflow 會上傳到 PyPI。

PyPI trusted-publisher 設定必須與 repo 一致：owner `Suyw-0123`、repo `md-to-pdf-cli`、
workflow `publish.yml`、environment 留空。

### 打包註記

- backend 是 `uv_build`；`[tool.uv.build-backend] module-name = "md2pdf"` 把發布名稱
  `md-to-pdf-cli` 對應到 import 套件 `md2pdf`。
- `uv build` 會自動把 `src/md2pdf/assets/` 下的一切（KaTeX + 字型、mermaid、模板、CSS）
  打進 wheel——不需 manifest。
- 正式 PyPI 有**名稱相似度過濾器**（TestPyPI 沒有）；這就是為什麼名稱是 `md-to-pdf-cli`
  而非 `markdown-to-pdf`。
- `pyproject.toml` 裡作者信箱 `su.willie.gm@gmail.com` 是刻意的——不要「修正」它。

## 新增功能：東西放哪

| 你想… | 動 |
|-------|----|
| 加一個 CLI 旗標 | `cli.py`（`Option` + `_apply_overrides`） |
| 加一個設定項 | `config.py`（dataclass + `from_dict`）+ `_SAMPLE_TOML` |
| 改 Markdown 解析 | `markdown_render.py`（`build_parser` / 外掛） |
| 改頁面樣式 | `assets/default.css`（或記錄一個 `--md2pdf-*` 變數） |
| 改 HTML 外殼 / readiness | `assets/template.html.j2` + `html_template.py` |
| 改 PDF/頁面選項 | `pdf_render.py`（`pdf_kwargs`） |
| 修圖片解析 | `images.py` |
