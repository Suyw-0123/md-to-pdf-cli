from pathlib import Path

from md2pdf.config import Config, Margin, load_config


def test_defaults():
    c = Config()
    assert c.output.page_size == "A4"
    assert c.features.math and c.features.mermaid
    assert c.footer.enabled is True
    assert "pageNumber" in c.footer.template
    assert c.header.enabled is False


def test_load_from_toml(tmp_path: Path):
    cfg = tmp_path / "md2pdf.toml"
    cfg.write_text(
        """
[output]
page_size = "Letter"
landscape = true
margin = { top = "1cm", bottom = "1cm", left = "1cm", right = "1cm" }

[theme]
css = ["a.css", "b.css"]
code_style = "monokai"

[features]
math = false
toc = true
""",
        encoding="utf-8",
    )
    c = load_config(cfg)
    assert c.output.page_size == "Letter"
    assert c.output.landscape is True
    assert c.output.margin == Margin(top="1cm", bottom="1cm", left="1cm", right="1cm")
    assert c.theme.css == ["a.css", "b.css"]
    assert c.theme.code_style == "monokai"
    assert c.features.math is False
    assert c.features.toc is True
    # mermaid not specified -> default True
    assert c.features.mermaid is True
    assert c.base_dir == cfg.resolve().parent


def test_load_missing_returns_defaults(tmp_path: Path):
    c = load_config(start=tmp_path)
    assert c.output.page_size == "A4"


def test_resolved_css_paths(tmp_path: Path):
    (tmp_path / "md2pdf.toml").write_text('[theme]\ncss = ["theme.css"]\n', encoding="utf-8")
    c = load_config(tmp_path / "md2pdf.toml")
    paths = c.resolved_css_paths()
    assert paths == [tmp_path / "theme.css"]
