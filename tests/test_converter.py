"""End-to-end conversion test. Requires a Chromium install (playwright)."""

from pathlib import Path

import pytest

from md2pdf.config import Config
from md2pdf.converter import convert, default_output_path

FIXTURES = Path(__file__).parent / "fixtures"


def test_default_output_path():
    assert default_output_path(Path("/x/doc.md")) == Path("/x/doc.pdf")


@pytest.mark.slow
def test_convert_sample_end_to_end(tmp_path: Path):
    out = tmp_path / "sample.pdf"
    config = Config()
    result = convert(FIXTURES / "sample.md", out, config)

    assert result.output_path == out
    assert out.is_file()
    assert out.stat().st_size > 1000

    from pypdf import PdfReader

    reader = PdfReader(str(out))
    # Long table + content should span multiple pages.
    assert len(reader.pages) >= 2

    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    # Chinese preserved. Chromium positions each CJK glyph individually, so
    # pypdf may insert spaces between them; normalize before comparing.
    compact = text.replace(" ", "").replace("\n", "")
    assert "範例文件" in compact  # Chinese encoding preserved (no mojibake)
    assert "保真度優先" in compact
    assert "greet" in text  # code content present
    # PDF outline/bookmarks generated from headings
    assert reader.outline


def test_convert_missing_input_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        convert(tmp_path / "nope.md", tmp_path / "o.pdf", Config())


def _count_pdf_images(path: Path) -> int:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    count = 0
    for page in reader.pages:
        resources = page.get("/Resources") or {}
        xobjects = resources.get("/XObject") or {}
        for obj in xobjects.values():
            if obj.get_object().get("/Subtype") == "/Image":
                count += 1
    return count


@pytest.mark.slow
def test_relative_parent_image_loads(tmp_path: Path):
    """Regression: images referenced with ../ must render (not broken).

    Chromium blocks file:// subresources from an about:blank origin, so the
    renderer must load the page from a file:// document instead.
    """
    import shutil

    (tmp_path / "reports").mkdir()
    (tmp_path / "docs").mkdir()
    shutil.copy(FIXTURES / "logo.png", tmp_path / "reports" / "fig.png")
    md = tmp_path / "docs" / "doc.md"
    md.write_text("# Doc\n\n![figure](../reports/fig.png)\n", encoding="utf-8")

    out = tmp_path / "doc.pdf"
    convert(md, out, Config())
    assert _count_pdf_images(out) == 1  # image embedded, not broken
