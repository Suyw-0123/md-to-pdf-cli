"""Markdown -> HTML conversion built on markdown-it-py.

Responsibilities:
- CommonMark + GFM tables + footnotes/deflist/tasklists.
- Inline/block math via dollarmath, emitted with KaTeX delimiters so the
  browser-side auto-render can typeset it.
- Server-side code highlighting via Pygments (deterministic, no browser).
- ```mermaid``` fences passed through as ``<pre class="mermaid">`` for the
  browser-side mermaid runtime.
- Heading anchors + optional table-of-contents extraction.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

from markdown_it import MarkdownIt
from mdit_py_plugins.anchors import anchors_plugin
from mdit_py_plugins.deflist import deflist_plugin
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.footnote import footnote_plugin
from mdit_py_plugins.front_matter import front_matter_plugin
from mdit_py_plugins.tasklists import tasklists_plugin
from pygments import highlight as _pyg_highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound

from .config import FeaturesConfig


@dataclass
class Heading:
    level: int
    text: str
    anchor: str


@dataclass
class RenderedDoc:
    html: str
    title: str
    headings: list[Heading] = field(default_factory=list)
    toc_html: str = ""


def _math_renderer(content: str, options: dict) -> str:
    """Wrap math in KaTeX-compatible delimiters for browser auto-render."""
    if options.get("display_mode"):
        return "\\[" + content + "\\]"
    return "\\(" + content + "\\)"


def _highlight(code: str, lang: str, _attrs: str) -> str:
    """Pygments-based fence highlighter.

    Returns markup starting with ``<pre`` so markdown-it does not re-wrap it.
    ``mermaid`` fences are passed through untouched for the browser runtime.
    """
    lang = (lang or "").strip()
    if lang.lower() == "mermaid":
        return f'<pre class="mermaid">{html.escape(code)}</pre>'
    try:
        lexer = get_lexer_by_name(lang) if lang else guess_lexer(code)
    except (ClassNotFound, ValueError):
        lexer = get_lexer_by_name("text")
    # nowrap=True yields only the token <span>s; we add a <pre class="highlight">
    # wrapper so Pygments' ``.highlight ...`` style rules apply.
    inner = _pyg_highlight(code, lexer, HtmlFormatter(nowrap=True))
    lang_class = f" language-{html.escape(lang)}" if lang else ""
    return f'<pre class="highlight{lang_class}"><code>{inner}</code></pre>\n'


def pygments_css(style: str = "default") -> str:
    """CSS rules for the requested Pygments style, scoped to ``.highlight``."""
    try:
        formatter = HtmlFormatter(style=style)
    except ClassNotFound:
        formatter = HtmlFormatter(style="default")
    return formatter.get_style_defs(".highlight")


def build_parser(features: FeaturesConfig) -> MarkdownIt:
    md = MarkdownIt("commonmark", {"highlight": _highlight})
    md.enable(["table", "strikethrough"])
    md.use(front_matter_plugin)
    md.use(footnote_plugin)
    md.use(deflist_plugin)
    md.use(tasklists_plugin, enabled=True)
    md.use(anchors_plugin, min_level=1, max_level=3)
    if features.math:
        md.use(dollarmath_plugin, double_inline=True, renderer=_math_renderer)
    return md


_FRONT_MATTER_TITLE = re.compile(r"^title\s*:\s*(.+?)\s*$", re.MULTILINE)


def _extract_front_matter_title(tokens) -> str | None:
    for tok in tokens:
        if tok.type == "front_matter":
            m = _FRONT_MATTER_TITLE.search(tok.content or "")
            if m:
                return m.group(1).strip().strip("'\"")
            return None
    return None


def _collect_headings(tokens) -> list[Heading]:
    headings: list[Heading] = []
    for i, tok in enumerate(tokens):
        if tok.type == "heading_open":
            level = int(tok.tag[1])
            anchor = dict(tok.attrs or {}).get("id", "")
            text = ""
            if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                text = tokens[i + 1].content
            headings.append(Heading(level=level, text=text, anchor=anchor))
    return headings


def _build_toc_html(headings: list[Heading]) -> str:
    items = [h for h in headings if h.anchor and 1 <= h.level <= 3]
    if not items:
        return ""
    min_level = min(h.level for h in items)
    parts = ['<nav class="toc"><div class="toc-title">目錄</div><ul>']
    for h in items:
        indent = h.level - min_level
        parts.append(
            f'<li class="toc-l{indent}"><a href="#{html.escape(h.anchor)}">'
            f"{html.escape(h.text)}</a></li>"
        )
    parts.append("</ul></nav>")
    return "".join(parts)


def render_markdown(
    source: str, features: FeaturesConfig, *, fallback_title: str = ""
) -> RenderedDoc:
    """Render Markdown source to an HTML body fragment + metadata."""
    md = build_parser(features)
    env: dict = {}
    tokens = md.parse(source, env)
    body = md.renderer.render(tokens, md.options, env)

    headings = _collect_headings(tokens)
    title = _extract_front_matter_title(tokens)
    if not title:
        title = next((h.text for h in headings if h.level == 1), "") or fallback_title

    toc_html = _build_toc_html(headings) if features.toc else ""
    return RenderedDoc(html=body, title=title, headings=headings, toc_html=toc_html)
