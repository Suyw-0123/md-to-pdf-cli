"""Typer CLI for md2pdf.

Usage:
    md2pdf <input.md> [-o output.pdf] [options]   # convert (default command)
    md2pdf convert <input.md> [options]            # same, explicit
    md2pdf init                                    # scaffold md2pdf.toml + theme

CLI flags override values from the config file, which override built-in
defaults.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from typer._click.core import Context as ClickContext
from typer._click.exceptions import UsageError  # vendored; matches TyperGroup
from typer.core import TyperGroup

from . import __version__
from .config import Config, Margin, load_config
from .converter import convert as convert_file
from .pdf_render import BrowserNotInstalledError

_console = Console()
_err = Console(stderr=True)


class DefaultGroup(TyperGroup):
    """A command group that falls back to ``convert`` for unknown commands.

    Lets ``md2pdf file.md`` work as a shorthand for ``md2pdf convert file.md``
    while keeping real subcommands like ``init`` available.
    """

    default_command = "convert"

    def resolve_command(self, ctx: ClickContext, args: list[str]):
        try:
            return super().resolve_command(ctx, args)
        except UsageError:
            if args and not args[0].startswith("-"):
                return super().resolve_command(ctx, [self.default_command, *args])
            raise


app = typer.Typer(
    cls=DefaultGroup,
    add_completion=False,
    no_args_is_help=True,
    help="Convert Markdown to PDF via headless Chromium.",
)


def _version_callback(value: bool) -> None:
    if value:
        _console.print(f"md2pdf {__version__}")
        raise typer.Exit()


@app.callback()
def _main(
    _version: bool | None = typer.Option(
        None, "--version", callback=_version_callback, is_eager=True, help="Show version and exit."
    ),
) -> None:
    """md2pdf — Markdown to PDF."""


@app.command()
def convert(
    input: Path = typer.Argument(..., help="Input Markdown (.md) file."),
    output: Path | None = typer.Option(
        None, "-o", "--output", help="Output PDF path (default: alongside input)."
    ),
    config_path: Path | None = typer.Option(None, "-c", "--config", help="Path to md2pdf.toml."),
    css: list[Path] = typer.Option([], "--css", help="Extra CSS file(s); repeatable."),
    page_size: str | None = typer.Option(None, "--page-size", help="A4, Letter, Legal, ..."),
    margin: str | None = typer.Option(
        None, "--margin", help="Margin applied to all sides, e.g. 2cm."
    ),
    landscape: bool | None = typer.Option(None, "--landscape/--portrait", help="Page orientation."),
    code_style: str | None = typer.Option(None, "--code-style", help="Pygments style name."),
    font: str | None = typer.Option(None, "--font", help="CSS font-family stack."),
    toc: bool | None = typer.Option(None, "--toc/--no-toc", help="Generate a table of contents."),
    math: bool | None = typer.Option(None, "--math/--no-math", help="Render LaTeX math (KaTeX)."),
    mermaid: bool | None = typer.Option(
        None, "--mermaid/--no-mermaid", help="Render mermaid diagrams."
    ),
    embed_images: bool | None = typer.Option(
        None, "--embed-images/--no-embed-images", help="Inline images as data URIs."
    ),
    header: str | None = typer.Option(None, "--header", help="Header HTML (inner)."),
    footer: str | None = typer.Option(None, "--footer", help="Footer HTML (inner)."),
) -> None:
    """Convert INPUT Markdown to PDF."""
    try:
        config = load_config(config_path)
        _apply_overrides(
            config,
            css=css,
            page_size=page_size,
            margin=margin,
            landscape=landscape,
            code_style=code_style,
            font=font,
            toc=toc,
            math=math,
            mermaid=mermaid,
            embed_images=embed_images,
            header=header,
            footer=footer,
        )
        result = convert_file(input, output, config)
    except BrowserNotInstalledError as exc:
        _err.print(f"[yellow]{exc}[/yellow]")
        raise typer.Exit(code=1) from exc
    except FileNotFoundError as exc:
        _err.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except Exception as exc:  # noqa: BLE001 - surface a clean message to the CLI user
        _err.print(f"[red]Conversion failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    _console.print(f"[green]✓[/green] {result.input_path} → {result.output_path}")


def _apply_overrides(
    config: Config,
    *,
    css: list[Path],
    page_size: str | None,
    margin: str | None,
    landscape: bool | None,
    code_style: str | None,
    font: str | None,
    toc: bool | None,
    math: bool | None,
    mermaid: bool | None,
    embed_images: bool | None,
    header: str | None,
    footer: str | None,
) -> None:
    if page_size is not None:
        config.output.page_size = page_size
    if margin is not None:
        config.output.margin = Margin(top=margin, bottom=margin, left=margin, right=margin)
    if landscape is not None:
        config.output.landscape = landscape
    if code_style is not None:
        config.theme.code_style = code_style
    if font is not None:
        config.theme.font_family = font
    if css:
        # CLI-provided CSS resolves relative to CWD; append (later wins).
        config.theme.css = config.theme.css + [str(p.resolve()) for p in css]
    if toc is not None:
        config.features.toc = toc
    if math is not None:
        config.features.math = math
    if mermaid is not None:
        config.features.mermaid = mermaid
    if embed_images is not None:
        config.features.embed_images = embed_images
    if header is not None:
        config.header.enabled = True
        config.header.template = header
    if footer is not None:
        config.footer.enabled = True
        config.footer.template = footer


_SAMPLE_TOML = """\
# md2pdf configuration. All sections are optional.

[output]
page_size = "A4"      # A4, Letter, Legal, ...
landscape = false
margin = { top = "2cm", bottom = "2cm", left = "1.8cm", right = "1.8cm" }

[theme]
base = "default"
css = ["theme.css"]   # extra CSS, appended after the default theme
code_style = "default" # any Pygments style name
# font_family = '"Noto Sans CJK TC", "Microsoft JhengHei", sans-serif'

[features]
math = true
mermaid = true
toc = false
embed_images = false  # inline local images as data URIs for a self-contained PDF

[footer]
enabled = true
# Placeholders: pageNumber, totalPages, title, date, url
template = '<span class="pageNumber"></span> / <span class="totalPages"></span>'

[header]
enabled = false
template = '<span class="title"></span>'
"""

_SAMPLE_CSS = """\
/* Custom theme overrides for md2pdf. Loaded after the default theme. */
:root {
  --md2pdf-accent: #0969da;
}
/* Example: a colored H1 underline */
h1 { border-bottom-color: var(--md2pdf-accent); }
"""


@app.command()
def init(
    directory: Path = typer.Argument(Path("."), help="Where to write the config files."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing files."),
) -> None:
    """Scaffold a md2pdf.toml and a starter theme.css in DIRECTORY."""
    directory.mkdir(parents=True, exist_ok=True)
    targets = [(directory / "md2pdf.toml", _SAMPLE_TOML), (directory / "theme.css", _SAMPLE_CSS)]

    for path, content in targets:
        if path.exists() and not force:
            _console.print(f"[yellow]skip[/yellow] {path} (exists; use --force)")
            continue
        path.write_text(content, encoding="utf-8")
        _console.print(f"[green]✓[/green] wrote {path}")
    _print_config_help()


def _print_config_help() -> None:
    """Explain md2pdf.toml and walk through every setting as a table."""
    _console.print(
        "\n"
        "[bold]md2pdf.toml[/bold] is auto-loaded from the current directory whenever you run md2pdf. "
        "\n"
        "The lookup order is [bold]CLI flags > md2pdf.toml > built-in defaults[/bold],"
        "\n"
        "so the file is just a place to make your preferred defaults stick. Every section and "
        "key is optional — keep what you want to change, delete the rest."
        "\n"
    )

    table = Table(
        title="md2pdf.toml settings:",
        title_style="bold",
        title_justify="left",
        header_style="bold",
        show_lines=True,
        pad_edge=False,
    )
    table.add_column("Section", style="cyan", no_wrap=True)
    table.add_column("Key", style="green", no_wrap=True)
    table.add_column("Default", style="dim", no_wrap=True)
    table.add_column("What it does")

    rows: list[tuple[str, str, str, str]] = [
        ("[output]", "page_size", "A4", "Paper format passed to Chromium: A4, Letter, Legal, ..."),
        ("", "landscape", "false", "Rotate the page to landscape orientation."),
        (
            "",
            "margin",
            "2cm / 1.8cm",
            "Page margins as an inline table: top, bottom, left, right (any CSS length).",
        ),
        (
            "[theme]",
            "base",
            "default",
            'Named base theme to start from (reserved; only "default" today).',
        ),
        (
            "",
            "css",
            "[]",
            "Extra stylesheets appended after the base theme (later files win). "
            'Relative paths resolve against the config file; e.g. css = ["theme.css"].',
        ),
        (
            "",
            "font_family",
            "CJK-first stack",
            "CSS font stack for body text. CJK faces are listed first so Chinese/"
            "Japanese/Korean text renders instead of tofu boxes.",
        ),
        (
            "",
            "code_style",
            "default",
            "Pygments style name used for syntax-highlighted code blocks.",
        ),
        ("[features]", "math", "true", "Parse $...$ / $$...$$ and render it with KaTeX."),
        ("", "mermaid", "true", "Render ```mermaid code fences into diagrams."),
        ("", "toc", "false", "Prepend a generated table-of-contents page."),
        (
            "",
            "embed_images",
            "false",
            "Inline local images as base64 data URIs for a single self-contained PDF.",
        ),
        (
            "[header]\n[footer]",
            "enabled",
            "footer: true\nheader: false",
            "Turn each banner on or off. The footer is on by default, the header off.",
        ),
        (
            "",
            "template",
            "—",
            "Inner HTML for the banner. Placeholders: pageNumber, totalPages, title, date, url.",
        ),
    ]
    for section, key, default, desc in rows:
        # Escape the leading [ so Rich doesn't treat [output] etc. as markup.
        section_cell = section.replace("[", r"\[") if section else ""
        table.add_row(section_cell, key, default, desc)

    _console.print(table)

    _console.print("\n")
    _console.print("Full reference: [bold]md2pdf --help[/bold] and the Configuration wiki page.")
    _console.print("\n")


if __name__ == "__main__":
    app()
