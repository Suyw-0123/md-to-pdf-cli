"""Configuration schema and loading.

Precedence when building the final config: CLI flags > config file > built-in
defaults. The CLI layer (``cli.py``) is responsible for applying CLI overrides
on top of the :class:`Config` returned by :func:`load_config`.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path

#: Default font stack. Lists common Traditional/Simplified Chinese faces first
#: so CJK text renders with a real CJK font instead of tofu/garbled glyphs.
DEFAULT_FONT_FAMILY = (
    '"Noto Sans CJK TC", "Noto Sans CJK SC", "Microsoft JhengHei", '
    '"PingFang TC", "Source Han Sans TC", "WenQuanYi Micro Hei", sans-serif'
)

#: Default footer: centered "current / total" page numbers. The placeholder
#: spans (``pageNumber``/``totalPages``) are filled in by Chromium at print time.
DEFAULT_FOOTER_TEMPLATE = '<span class="pageNumber"></span> / <span class="totalPages"></span>'

CONFIG_FILENAME = "md2pdf.toml"


@dataclass
class Margin:
    top: str = "2cm"
    bottom: str = "2cm"
    left: str = "1.8cm"
    right: str = "1.8cm"

    @classmethod
    def from_dict(cls, data: dict) -> Margin:
        base = cls()
        return replace(
            base,
            **{k: str(v) for k, v in data.items() if k in {"top", "bottom", "left", "right"}},
        )

    def as_playwright(self) -> dict[str, str]:
        return {"top": self.top, "bottom": self.bottom, "left": self.left, "right": self.right}


@dataclass
class OutputConfig:
    page_size: str = "A4"
    landscape: bool = False
    margin: Margin = field(default_factory=Margin)

    @classmethod
    def from_dict(cls, data: dict) -> OutputConfig:
        base = cls()
        return replace(
            base,
            page_size=str(data.get("page_size", base.page_size)),
            landscape=bool(data.get("landscape", base.landscape)),
            margin=Margin.from_dict(data["margin"])
            if isinstance(data.get("margin"), dict)
            else base.margin,
        )


@dataclass
class ThemeConfig:
    base: str = "default"
    #: Extra CSS files appended after the base theme (later files win).
    css: list[str] = field(default_factory=list)
    font_family: str = DEFAULT_FONT_FAMILY
    #: Pygments style name used to generate code-highlight CSS.
    code_style: str = "default"

    @classmethod
    def from_dict(cls, data: dict) -> ThemeConfig:
        base = cls()
        css = data.get("css", base.css)
        if isinstance(css, str):
            css = [css]
        return replace(
            base,
            base=str(data.get("base", base.base)),
            css=[str(c) for c in css],
            font_family=str(data.get("font_family", base.font_family)),
            code_style=str(data.get("code_style", base.code_style)),
        )


@dataclass
class BannerConfig:
    """A page header or footer rendered in the margin by Chromium.

    ``template`` is the *inner* HTML; the renderer wraps it in a styled
    container. Available placeholder classes (filled by Chromium): ``title``,
    ``date``, ``url``, ``pageNumber``, ``totalPages``.
    """

    enabled: bool = False
    template: str = ""

    @classmethod
    def from_dict(
        cls, data: dict, *, default_enabled: bool = False, default_template: str = ""
    ) -> BannerConfig:
        return cls(
            enabled=bool(data.get("enabled", default_enabled)),
            template=str(data.get("template", default_template)),
        )


@dataclass
class FeaturesConfig:
    math: bool = True
    mermaid: bool = True
    toc: bool = False
    #: Inline local images as base64 data URIs so the PDF is self-contained.
    embed_images: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> FeaturesConfig:
        base = cls()
        return replace(
            base,
            math=bool(data.get("math", base.math)),
            mermaid=bool(data.get("mermaid", base.mermaid)),
            toc=bool(data.get("toc", base.toc)),
            embed_images=bool(data.get("embed_images", base.embed_images)),
        )


@dataclass
class Config:
    output: OutputConfig = field(default_factory=OutputConfig)
    theme: ThemeConfig = field(default_factory=ThemeConfig)
    header: BannerConfig = field(default_factory=BannerConfig)
    footer: BannerConfig = field(
        default_factory=lambda: BannerConfig(enabled=True, template=DEFAULT_FOOTER_TEMPLATE)
    )
    features: FeaturesConfig = field(default_factory=FeaturesConfig)
    #: Directory the config file lived in; relative theme CSS paths resolve here.
    base_dir: Path = field(default_factory=Path.cwd)

    @classmethod
    def from_dict(cls, data: dict, *, base_dir: Path) -> Config:
        return cls(
            output=OutputConfig.from_dict(data.get("output", {})),
            theme=ThemeConfig.from_dict(data.get("theme", {})),
            header=BannerConfig.from_dict(data.get("header", {}), default_enabled=False),
            footer=BannerConfig.from_dict(
                data.get("footer", {}),
                default_enabled=True,
                default_template=DEFAULT_FOOTER_TEMPLATE,
            ),
            features=FeaturesConfig.from_dict(data.get("features", {})),
            base_dir=base_dir,
        )

    def resolved_css_paths(self) -> list[Path]:
        """Absolute paths to the user's extra CSS files."""
        out: list[Path] = []
        for entry in self.theme.css:
            p = Path(entry).expanduser()
            out.append(p if p.is_absolute() else (self.base_dir / p))
        return out


def find_config_file(explicit: Path | None, start: Path | None = None) -> Path | None:
    """Locate a config file: explicit path wins, else ``md2pdf.toml`` in CWD."""
    if explicit is not None:
        if not explicit.is_file():
            raise FileNotFoundError(f"Config file not found: {explicit}")
        return explicit
    candidate = (start or Path.cwd()) / CONFIG_FILENAME
    return candidate if candidate.is_file() else None


def load_config(explicit: Path | None = None, *, start: Path | None = None) -> Config:
    """Load configuration, falling back to built-in defaults when absent."""
    path = find_config_file(explicit, start=start)
    if path is None:
        return Config()
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    return Config.from_dict(data, base_dir=path.resolve().parent)
