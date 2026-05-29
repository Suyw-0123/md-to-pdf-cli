"""Image source rewriting.

Fixes the common "broken image after conversion" bug: relative ``<img src>``
paths are resolved against the Markdown file's directory and turned into
absolute ``file://`` URLs (or inlined as base64 data URIs when configured).
Remote (http/https) and existing data URIs are left untouched.
"""

from __future__ import annotations

import base64
import mimetypes
import re
from pathlib import Path
from urllib.parse import quote

# Matches the src attribute of an <img> tag (single or double quoted).
_IMG_SRC = re.compile(r'(<img\b[^>]*?\bsrc\s*=\s*)(["\'])(.*?)\2', re.IGNORECASE | re.DOTALL)

_REMOTE = re.compile(r"^(?:https?:|data:|file:|//)", re.IGNORECASE)


def _to_file_url(path: Path) -> str:
    return "file://" + quote(str(path))


def _to_data_uri(path: Path) -> str | None:
    mime, _ = mimetypes.guess_type(path.name)
    if mime is None:
        mime = "application/octet-stream"
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    return f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")


def rewrite_image_sources(html_body: str, base_dir: Path, *, embed: bool = False) -> str:
    """Rewrite local image sources in ``html_body`` so they resolve at print time.

    Args:
        html_body: HTML fragment produced by the Markdown renderer.
        base_dir: Directory of the source ``.md`` file; relative srcs resolve here.
        embed: When True, inline local images as base64 data URIs.
    """

    def repl(match: re.Match) -> str:
        prefix, quote_ch, src = match.group(1), match.group(2), match.group(3)
        if not src or _REMOTE.match(src.strip()):
            return match.group(0)
        candidate = Path(src)
        abs_path = candidate if candidate.is_absolute() else (base_dir / candidate)
        abs_path = abs_path.expanduser()
        if not abs_path.is_file():
            # Leave unresolved sources as-is so the failure is visible/debuggable.
            return match.group(0)
        if embed:
            new_src = _to_data_uri(abs_path) or _to_file_url(abs_path.resolve())
        else:
            new_src = _to_file_url(abs_path.resolve())
        return f"{prefix}{quote_ch}{new_src}{quote_ch}"

    return _IMG_SRC.sub(repl, html_body)
