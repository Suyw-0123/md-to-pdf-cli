from pathlib import Path

from md2pdf.images import rewrite_image_sources

FIXTURES = Path(__file__).parent / "fixtures"


def test_relative_local_becomes_file_url():
    body = '<p><img src="logo.png" alt="x"></p>'
    out = rewrite_image_sources(body, FIXTURES, embed=False)
    assert 'src="file://' in out
    assert "logo.png" in out


def test_embed_produces_data_uri():
    body = '<img src="logo.png">'
    out = rewrite_image_sources(body, FIXTURES, embed=True)
    assert "data:image/png;base64," in out


def test_remote_untouched():
    body = '<img src="https://example.com/a.png">'
    assert rewrite_image_sources(body, FIXTURES) == body


def test_existing_data_uri_untouched():
    body = '<img src="data:image/png;base64,AAAA">'
    assert rewrite_image_sources(body, FIXTURES) == body


def test_missing_file_left_as_is():
    body = '<img src="does-not-exist.png">'
    assert rewrite_image_sources(body, FIXTURES) == body


def test_absolute_path_resolved():
    abs_src = (FIXTURES / "logo.png").resolve()
    body = f'<img src="{abs_src}">'
    out = rewrite_image_sources(body, Path("/tmp"), embed=False)
    assert "file://" in out
