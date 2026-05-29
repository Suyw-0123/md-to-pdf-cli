from md2pdf.config import FeaturesConfig
from md2pdf.markdown_render import pygments_css, render_markdown


def _features(**kw):
    f = FeaturesConfig()
    for k, v in kw.items():
        setattr(f, k, v)
    return f


def test_code_highlight_starts_with_pre():
    doc = render_markdown("```python\nprint(1)\n```\n", _features())
    assert '<pre class="highlight language-python">' in doc.html
    assert "<span" in doc.html  # pygments tokens
    # must not be double-wrapped in <pre><code><pre>
    assert "<pre><code>" not in doc.html


def test_math_delimiters_emitted():
    doc = render_markdown("inline $a+b$ and\n\n$$x^2$$\n", _features(math=True))
    assert "\\(" in doc.html and "\\)" in doc.html
    assert "\\[" in doc.html and "\\]" in doc.html


def test_math_disabled_leaves_dollars():
    doc = render_markdown("inline $a+b$ text\n", _features(math=False))
    assert "\\(" not in doc.html


def test_mermaid_passthrough():
    doc = render_markdown("```mermaid\nflowchart LR\nA-->B\n```\n", _features())
    assert '<pre class="mermaid">' in doc.html
    assert "flowchart LR" in doc.html
    assert "highlight" not in doc.html  # mermaid not run through pygments


def test_title_from_front_matter():
    doc = render_markdown("---\ntitle: My Doc\n---\n\n# Other\n", _features(), fallback_title="fb")
    assert doc.title == "My Doc"


def test_title_falls_back_to_h1_then_filename():
    assert render_markdown("# Heading One\n", _features()).title == "Heading One"
    assert render_markdown("plain text\n", _features(), fallback_title="fb").title == "fb"


def test_toc_generation():
    md = "# A\n\n## B\n\n## C\n"
    assert render_markdown(md, _features(toc=False)).toc_html == ""
    toc = render_markdown(md, _features(toc=True)).toc_html
    assert 'class="toc"' in toc
    assert "#a" in toc and "#b" in toc


def test_table_rendered():
    doc = render_markdown("| a | b |\n|---|---|\n| 1 | 2 |\n", _features())
    assert "<table>" in doc.html and "<th>" in doc.html


def test_pygments_css_scoped():
    css = pygments_css("default")
    assert ".highlight" in css
