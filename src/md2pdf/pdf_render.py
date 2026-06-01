"""Render a self-contained HTML document to PDF via Playwright/Chromium.

The critical correctness detail: we do not call ``page.pdf()`` until the page
signals ``window.__md2pdf_ready`` (set after KaTeX typesetting, mermaid
rendering, and font loading complete). This prevents the "printed too early /
broken diagrams" class of bugs.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from .config import Config

#: How long to wait for client-side math/diagram rendering before giving up.
_RENDER_TIMEOUT_MS = 30_000

_EMPTY_BANNER = "<span></span>"

#: Set this env var to a falsey value to opt out of the first-run auto-download
#: (e.g. in CI where you provision the browser yourself).
_AUTO_INSTALL_ENV = "MD2PDF_AUTO_INSTALL_BROWSER"

#: Set this env var truthy to launch Chromium with ``--no-sandbox`` +
#: ``--disable-dev-shm-usage``. Required inside most containers (the official
#: Docker image sets it); leave it unset for normal installs so the browser
#: keeps its sandbox.
_NO_SANDBOX_ENV = "MD2PDF_CHROMIUM_NO_SANDBOX"

_TRUTHY = {"1", "true", "yes", "on"}

_INSTALL_HINT = (
    "Chromium is not installed for Playwright and the automatic download failed.\n"
    "Install it manually once with:\n"
    "    playwright install chromium\n"
    "If you installed md2pdf as a uv tool:\n"
    "    uv tool run --from md-to-pdf-cli playwright install chromium"
)


class BrowserNotInstalledError(RuntimeError):
    """Raised when the Chromium browser binary is missing and can't be installed."""


def _is_missing_browser_error(exc: PlaywrightError) -> bool:
    message = str(exc)
    return "Executable doesn't exist" in message or "playwright install" in message


def _auto_install_enabled() -> bool:
    return os.environ.get(_AUTO_INSTALL_ENV, "1").strip().lower() not in {"0", "false", "no", ""}


def _chromium_launch_args() -> list[str]:
    if os.environ.get(_NO_SANDBOX_ENV, "").strip().lower() in _TRUTHY:
        # --disable-dev-shm-usage avoids Chromium crashing on the small /dev/shm
        # that containers ship with by default.
        return ["--no-sandbox", "--disable-dev-shm-usage"]
    return []


def _install_chromium() -> bool:
    """Download the Chromium binary Playwright needs. Returns True on success.

    Runs ``playwright install`` against the *current* interpreter so it works the
    same whether md2pdf was installed with pip, uv, or pipx — the browser lands
    in Playwright's shared per-user cache, so this only ever downloads once.
    """
    print(
        "md2pdf: Chromium isn't installed yet — downloading it once "
        "(~150 MB, this can take a minute)…",
        file=sys.stderr,
        flush=True,
    )
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0


def _launch_chromium(playwright):
    args = _chromium_launch_args()
    try:
        return playwright.chromium.launch(args=args)
    except PlaywrightError as exc:
        if not _is_missing_browser_error(exc):
            raise
        if not _auto_install_enabled() or not _install_chromium():
            raise BrowserNotInstalledError(_INSTALL_HINT) from exc
        # Retry once now that the browser should be present.
        try:
            return playwright.chromium.launch(args=args)
        except PlaywrightError as retry_exc:
            raise BrowserNotInstalledError(_INSTALL_HINT) from retry_exc


def _wrap_banner(inner: str) -> str:
    """Wrap user header/footer HTML in a sized, centered container.

    Chromium renders header/footer templates at a near-zero default font size,
    so an explicit size/width is required for anything to show up.
    """
    return (
        '<div style="font-size:9px; width:100%; padding:0 1cm; '
        'color:#57606a; text-align:center; -webkit-print-color-adjust:exact;">'
        f"{inner}</div>"
    )


def render_pdf(html: str, output_path: Path, config: Config) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    header, footer = config.header, config.footer
    display_hf = header.enabled or footer.enabled

    pdf_kwargs: dict = {
        "path": str(output_path),
        "format": config.output.page_size,
        "landscape": config.output.landscape,
        "print_background": True,
        "margin": config.output.margin.as_playwright(),
        "prefer_css_page_size": False,
        # tagged (accessible) PDF; required for Chromium to emit the heading
        # outline that becomes PDF bookmarks.
        "tagged": True,
        "outline": True,
    }
    if display_hf:
        pdf_kwargs["display_header_footer"] = True
        pdf_kwargs["header_template"] = (
            _wrap_banner(header.template) if header.enabled else _EMPTY_BANNER
        )
        pdf_kwargs["footer_template"] = (
            _wrap_banner(footer.template) if footer.enabled else _EMPTY_BANNER
        )

    with sync_playwright() as p:
        browser = _launch_chromium(p)
        try:
            page = browser.new_page()
            # Load via a temp file:// document rather than set_content(): Chromium
            # refuses to load local file:// images ("Not allowed to load local
            # resource") from an about:blank origin, but a file:// page may load
            # file:// subresources. This is what makes relative-path images work.
            with tempfile.TemporaryDirectory(prefix="md2pdf-") as tmpdir:
                tmp_html = Path(tmpdir) / "document.html"
                tmp_html.write_text(html, encoding="utf-8")
                page.goto(tmp_html.as_uri(), wait_until="load")
                page.wait_for_function("window.__md2pdf_ready === true", timeout=_RENDER_TIMEOUT_MS)
                page.emulate_media(media="print")
                page.pdf(**pdf_kwargs)
        finally:
            browser.close()

    return output_path
