from __future__ import annotations

from dataclasses import dataclass, field, replace

from .colors import Color, parse_color
from .errors import DslError
from .units import AUTO, Percent, Rect, Size, Thickness, parse_length, parse_thickness

DEFAULT_COLORS = {
    "dk1": "1E2761",
    "lt1": "FFFFFF",
    "dk2": "33415C",
    "lt2": "F2F6FC",
    "accent1": "2563EB",
    "accent2": "0EA5E9",
    "accent3": "14B8A6",
    "accent4": "F59E0B",
    "accent5": "EF4444",
    "accent6": "8B5CF6",
    "hlink": "2563EB",
    "folHlink": "7C3AED",
}

INHERITED_PROPS = (
    "fontfamily",
    "eastasianfontfamily",
    "fontsize",
    "fontweight",
    "fontstyle",
    "foreground",
    "lineheight",
    "textwrapping",
    "letterSpacing".lower(),
)

ALIGNMENTS = {"left", "center", "right", "stretch"}
VALIGNMENTS = {"top", "center", "bottom", "stretch"}
TRUE_VALUES = {"true", "1", "yes", "on"}
PADDING_TAGS = {"Border", "TextBlock", "List", "Cell"}


@dataclass
class Theme:
    colors: dict = field(default_factory=lambda: dict(DEFAULT_COLORS))
    major_latin: str = "Cambria"
    major_ea: str = "Microsoft YaHei"
    minor_latin: str = "Calibri"
    minor_ea: str = "Microsoft YaHei"


@dataclass
class RunSpec:
    text: str
    size: float = 18.0
    bold: bool = False
    italic: bool = False
    family: str = "Calibri"
    ea: str = "Microsoft YaHei"
    color: Color | None = None
    underline: bool = False
    spacing: float = 0.0


@dataclass
class Deck:
    width: int
    height: int
    theme: Theme
    root: "Element"
    slides: list = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    named_colors: dict = field(default_factory=dict)
    source: str | None = None

    @property
    def page_size(self):
        return Size(self.width, self.height)


class Element:
    __slots__ = (
        "tag",
        "props",
        "children",
        "parent",
        "line",
        "meta",
        "rect",
        "measured",
        "margin",
        "padding",
        "width",
        "height",
        "min_width",
        "max_width",
        "min_height",
        "max_height",
        "halign",
        "valign",
        "runs",
        "text",
        "prepared",
    )

    def __init__(self, tag, props=None, line=None):
        self.tag = tag
        self.props = {str(key).lower(): value for key, value in (props or {}).items()}
        self.children = []
        self.parent = None
        self.line = line
        self.meta = {}
        self.rect = Rect(0, 0, 0, 0)
        self.measured = Size(0, 0)
        self.margin = Thickness()
        self.padding = Thickness()
        self.width = None
        self.height = None
        self.min_width = None
        self.max_width = None
        self.min_height = None
        self.max_height = None
        self.halign = "stretch"
        self.valign = "stretch"
        self.runs = []
        self.text = ""
        self.prepared = False

    def add(self, child):
        child.parent = self
        self.children.append(child)
        return child

    def get(self, name, default=None):
        return self.props.get(str(name).lower(), default)

    def has(self, name):
        return str(name).lower() in self.props

    def get_bool(self, name, default=False):
        value = self.get(name)
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in TRUE_VALUES

    def get_float(self, name, default=None):
        value = self.get(name)
        if value is None:
            return default
        try:
            return float(str(value).strip())
        except ValueError as exc:
            raise DslError(f"invalid number {value!r} for {name}", element=self) from exc

    def get_length(self, name, default=None):
        raw = self.get(name)
        if raw is None:
            return default
        try:
            return parse_length(raw)
        except ValueError as exc:
            raise DslError(f"{name}: {exc}", element=self) from exc

    def get_color(self, name, named=None):
        raw = self.get(name)
        if raw is None:
            return None
        try:
            return parse_color(raw, named)
        except ValueError as exc:
            raise DslError(f"{name}: {exc}", element=self) from exc

    def text_content(self):
        return "".join(run.text for run in self.runs)

    def __repr__(self):
        name = self.get("Name")
        return f"<{self.tag}{' ' + name if name else ''} line={self.line}>"


def prepare(el):
    if el.prepared:
        return el
    el.prepared = True
    try:
        el.margin = parse_thickness(el.get("Margin"))
        el.padding = parse_thickness(el.get("Padding"))
        el.width = el.get_length("Width")
        el.height = el.get_length("Height")
        el.min_width = el.get_length("MinWidth")
        el.max_width = el.get_length("MaxWidth")
        el.min_height = el.get_length("MinHeight")
        el.max_height = el.get_length("MaxHeight")
    except DslError:
        raise
    except ValueError as exc:
        raise DslError(str(exc), element=el) from exc

    halign = str(el.get("HorizontalAlignment", "Stretch")).strip().lower()
    if halign not in ALIGNMENTS:
        raise DslError(f"invalid HorizontalAlignment {halign!r}", element=el)
    el.halign = halign
    valign = str(el.get("VerticalAlignment", "Stretch")).strip().lower()
    if valign not in VALIGNMENTS:
        raise DslError(f"invalid VerticalAlignment {valign!r}", element=el)
    el.valign = valign
    if el.padding != Thickness() and el.tag not in PADDING_TAGS:
        raise DslError(
            f"Padding is not supported on <{el.tag}>; wrap it in a <Border> or use Margin",
            element=el,
        )
    return el


def split_runs(runs):
    paragraphs = [[]]
    for run in runs:
        parts = run.text.split("\n")
        for index, part in enumerate(parts):
            if index:
                paragraphs.append([])
            if part:
                paragraphs[-1].append(replace(run, text=part))
    return paragraphs
