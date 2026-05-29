"""Top-level orchestration: Markdown file -> PDF file."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .html_template import build_html
from .images import rewrite_image_sources
from .markdown_render import render_markdown
from .pdf_render import render_pdf


@dataclass
class ConversionResult:
    input_path: Path
    output_path: Path
    title: str


def read_markdown(path: Path) -> str:
    """Read a Markdown file as UTF-8, transparently stripping a BOM.

    Using ``utf-8-sig`` fixes the garbled-Chinese bug seen when a BOM or
    mis-detected encoding leaks into the rendered output.
    """
    return path.read_text(encoding="utf-8-sig")


def default_output_path(input_path: Path) -> Path:
    return input_path.with_suffix(".pdf")


def convert(input_path: Path, output_path: Path | None, config: Config) -> ConversionResult:
    input_path = Path(input_path)
    if not input_path.is_file():
        raise FileNotFoundError(f"Input Markdown file not found: {input_path}")
    out = Path(output_path) if output_path else default_output_path(input_path)

    source = read_markdown(input_path)
    doc = render_markdown(source, config.features, fallback_title=input_path.stem)
    doc.html = rewrite_image_sources(
        doc.html, input_path.resolve().parent, embed=config.features.embed_images
    )
    html = build_html(doc, config)
    render_pdf(html, out, config)
    return ConversionResult(input_path=input_path, output_path=out, title=doc.title)
