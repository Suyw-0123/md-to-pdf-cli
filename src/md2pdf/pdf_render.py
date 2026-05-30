"""Render a self-contained HTML document to PDF via Playwright/Chromium.

The critical correctness detail: we do not call ``page.pdf()`` until the page
signals ``window.__md2pdf_ready`` (set after KaTeX typesetting, mermaid
rendering, and font loading complete). This prevents the "printed too early /
broken diagrams" class of bugs.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from .config import Config

#: How long to wait for client-side math/diagram rendering before giving up.
_RENDER_TIMEOUT_MS = 30_000

_EMPTY_BANNER = "<span></span>"

_INSTALL_HINT = (
    "Chromium is not installed for Playwright.\n"
    "Install it once with:\n"
    "    playwright install chromium\n"
    "If you installed md2pdf as a uv tool:\n"
    "    uv tool run --from md-to-pdf-cli playwright install chromium"
)


class BrowserNotInstalledError(RuntimeError):
    """Raised when the Chromium browser binary is missing."""


def _launch_chromium(playwright):
    try:
        return playwright.chromium.launch()
    except PlaywrightError as exc:
        if "Executable doesn't exist" in str(exc) or "playwright install" in str(exc):
            raise BrowserNotInstalledError(_INSTALL_HINT) from exc
        raise


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
