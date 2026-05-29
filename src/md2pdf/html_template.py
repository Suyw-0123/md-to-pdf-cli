"""Assemble a self-contained HTML document from rendered Markdown.

All assets (theme CSS, Pygments CSS, KaTeX, mermaid) are inlined so the page
renders identically whether loaded from ``file://`` or via ``set_content`` with
an ``about:blank`` base. KaTeX font files are embedded as data URIs for the
same reason.
"""

from __future__ import annotations

import base64
import functools
import re
from importlib.resources import files

from jinja2 import Environment

from .config import Config
from .markdown_render import RenderedDoc, pygments_css

_ASSETS = files("md2pdf") / "assets"

_FONT_URL = re.compile(r"url\(fonts/([A-Za-z0-9_\-]+\.woff2)\)")


def _read_asset(*parts: str) -> str:
    node = _ASSETS
    for p in parts:
        node = node / p
    return node.read_text(encoding="utf-8")


@functools.lru_cache(maxsize=1)
def _katex_css_inlined() -> str:
    """KaTeX CSS with its woff2 fonts inlined as data URIs (self-contained)."""
    css = _read_asset("vendor", "katex", "katex.min.css")
    fonts_dir = _ASSETS / "vendor" / "katex" / "fonts"

    def repl(match: re.Match) -> str:
        name = match.group(1)
        try:
            raw = (fonts_dir / name).read_bytes()
        except OSError:
            return match.group(0)
        b64 = base64.b64encode(raw).decode("ascii")
        return f"url(data:font/woff2;base64,{b64})"

    return _FONT_URL.sub(repl, css)


@functools.lru_cache(maxsize=1)
def _template():
    env = Environment(autoescape=False)  # body/CSS/JS are trusted, pre-escaped
    return env.from_string(_read_asset("template.html.j2"))


def build_html(doc: RenderedDoc, config: Config) -> str:
    features = config.features

    theme_css = _read_asset("default.css")
    extra_css = "\n".join(
        p.read_text(encoding="utf-8") for p in config.resolved_css_paths() if p.is_file()
    )

    context = {
        "lang": "zh-Hant",
        "title": doc.title or "Document",
        "body": doc.html,
        "toc_html": doc.toc_html,
        "font_family": config.theme.font_family,
        "theme_css": theme_css,
        "extra_css": extra_css,
        "pygments_css": pygments_css(config.theme.code_style),
        "math": features.math,
        "mermaid": features.mermaid,
    }

    if features.math:
        context["katex_css"] = _katex_css_inlined()
        context["katex_js"] = _read_asset("vendor", "katex", "katex.min.js")
        context["katex_autorender_js"] = _read_asset(
            "vendor", "katex", "contrib", "auto-render.min.js"
        )
    if features.mermaid:
        context["mermaid_js"] = _read_asset("vendor", "mermaid", "mermaid.min.js")

    return _template().render(**context)
