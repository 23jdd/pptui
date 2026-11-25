from __future__ import annotations

import os
import re
from pathlib import Path

from lxml import etree

from .colors import Color, parse_color
from .errors import DslError
from .model import Deck, Element, INHERITED_PROPS, RunSpec, Theme, prepare
from .units import AUTO, Percent, parse_length

SAFE_PARSER = etree.XMLParser(
    resolve_entities=False,
    no_network=True,
    huge_tree=False,
    remove_blank_text=False,
)

XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

VISUAL_TAGS = {
    "Canvas",
    "StackPanel",
    "Grid",
    "Border",
    "DockPanel",
    "TextBlock",
    "List",
    "Image",
    "Rectangle",
    "Ellipse",
    "RoundedRectangle",
    "Table",
    "Chart",
}

SHAPE_TAGS = {"Rectangle", "Ellipse", "RoundedRectangle"}

TEXT_TAGS = {"TextBlock", "Item", "Cell"}

_SKIP_TAGS = {"Grid.RowDefinitions", "Grid.ColumnDefinitions", "Table.Columns"}


def local_name(tag):
    if not isinstance(tag, str):
        return ""
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def _clean(text, preserve=False):
    if text is None:
        return ""
    if preserve:
        return text
    return re.sub(r"\s+", " ", text).strip()


def _attrs(xml_el):
    result = {}
    for key, value in xml_el.attrib.items():
        if key.startswith("{"):
            continue
        result[key] = value
    return result


def _font_size(text, default=18.0):
    if text is None:
        return default
    raw = str(text).strip().lower()
    match = re.match(r"^(-?\d+(?:\.\d+)?)\s*(pt|px|in|cm|mm)?$", raw)
    if not match:
        raise ValueError(f"invalid font size {text!r}")
    value = float(match.group(1))
    unit = match.group(2) or "pt"
    if unit == "pt":
        return value
    if unit == "px":
        return value * 0.75
    if unit == "in":
        return value * 72.0
    if unit == "cm":
        return value * 72.0 / 2.54
    return value * 72.0 / 25.4


def _line_height_pt(text):
    if text is None:
        return None
    raw = str(text).strip().lower()
    if raw.endswith("pt"):
        return float(raw[:-2])
    if raw.endswith("px"):
        return float(raw[:-2]) * 0.75
    return float(raw)


def _is_bold(props):
    value = props.get("fontweight", "")
    if str(props.get("bold", "")).strip().lower() in {"true", "1", "yes"}:
        return True
    return str(value).strip().lower() in {"bold", "semibold", "demibold", "black", "heavy", "700", "800", "900"}


def _is_italic(props):
    value = str(props.get("fontstyle", "")).strip().lower()
    return value in {"italic", "oblique"}


def make_run(text, props, ctx):
    return RunSpec(
        text=text,
        size=_font_size(props.get("fontsize"), 18.0),
        bold=_is_bold(props),
        italic=_is_italic(props),
        family=props.get("fontfamily") or ctx.theme.minor_latin,
        ea=props.get("eastasianfontfamily") or ctx.theme.minor_ea,
        color=_color(props.get("foreground"), ctx),
        underline=str(props.get("textdecoration", "")).strip().lower() == "underline",
        spacing=_letter_spacing(props.get("letterspacing")),
    )


def _letter_spacing(text):
    if text is None:
        return 0.0
    raw = str(text).strip().lower()
    if raw == "normal":
        return 0.0
    if raw.endswith("pt"):
        return float(raw[:-2])
    if raw.endswith("px"):
        return float(raw[:-2]) * 0.75
    return float(raw)


def _color(text, ctx):
    if text is None:
        return None
    try:
        return parse_color(text, ctx.named_colors)
    except ValueError as exc:
        raise DslError(str(exc)) from exc


def _collect_runs(xml_el, base_props, ctx):
    preserve = xml_el.get(XML_SPACE) == "preserve"
    segments = []

    def push(text, props, is_break=False):
        if text is None:
            return
        if is_break or preserve:
            cleaned = text
        else:
            cleaned = re.sub(r"\s+", " ", text)
        if cleaned or is_break:
            segments.append([cleaned, props, is_break])

    text_attr = xml_el.get("Text")
    if text_attr is not None:
        push(text_attr, base_props)
    push(xml_el.text, base_props)
    for child in xml_el:
        tag = local_name(child.tag)
        if tag == "Run":
            props = dict(base_props)
            props.update({key.lower(): value for key, value in _attrs(child).items()})
            push(child.text, props)
        elif tag == "LineBreak":
            push("\n", base_props, True)
        else:
            push("".join(child.itertext()), base_props)
        push(child.tail, base_props)

    for segment in segments:
        if not segment[2]:
            segment[0] = segment[0].lstrip()
            break
    for segment in reversed(segments):
        if not segment[2]:
            segment[0] = segment[0].rstrip()
            break

    runs = [make_run(text, props, ctx) for text, props, _ in segments if text]
    return runs


class Context:
    def __init__(self, theme, defaults, implicit, styles, named_colors, source):
        self.theme = theme
        self.defaults = defaults
        self.implicit = implicit
        self.styles = styles
        self.named_colors = named_colors
        self.source = source
        self.base_dir = Path(source).resolve().parent if source else Path.cwd()


def _defaults(theme):
    return {
        "Deck": {
            "FontFamily": theme.minor_latin,
            "EastAsianFontFamily": theme.minor_ea,
            "Foreground": "@text1",
        },
        "Slide": {"Layout": "Blank"},
        "TextBlock": {
            "FontSize": "18pt",
            "TextWrapping": "Wrap",
            "TextAlignment": "Left",
            "VerticalContentAlignment": "Top",
            "AutoFit": "Shrink",
        },
        "List": {
            "FontSize": "18pt",
            "Bullet": "Disc",
            "Indent": "0.3in",
            "ItemSpacing": "6pt",
            "TextAlignment": "Left",
            "VerticalContentAlignment": "Top",
            "AutoFit": "Shrink",
        },
        "Table": {
            "FontSize": "14pt",
            "TextAlignment": "Left",
            "CellPadding": "0.08in",
            "BorderBrush": "@lt2",
            "BorderThickness": "1pt",
        },
        "Image": {"Stretch": "Uniform"},
        "Border": {"Padding": "0"},
        "Grid": {},
        "Canvas": {},
        "StackPanel": {"Orientation": "Vertical", "Spacing": "0"},
        "DockPanel": {"LastChildFill": "True"},
        "Chart": {"Legend": "Bottom", "FontSize": "12pt"},
    }


def _style_key(text):
    raw = str(text).strip()
    match = re.match(r"^\{?StaticResource\s+([^}]+)\}?$", raw, re.I)
    if match:
        return match.group(1).strip()
    return raw


def _resolve_props(tag, attrs, parent, ctx):
    props = {}
    props.update({key.lower(): value for key, value in ctx.defaults.get(tag, {}).items()})
    if parent is not None:
        for key in INHERITED_PROPS:
            value = parent.props.get(key)
            if value is not None:
                props[key] = value
    props.update({key.lower(): value for key, value in ctx.implicit.get(tag, {}).items()})
    style_attr = attrs.get("Style")
    if style_attr:
        key = _style_key(style_attr)
        style = ctx.styles.get(key)
        if style is None:
            raise DslError(f"unknown Style {key!r}")
        props.update({name.lower(): value for name, value in style.items()})
    props.update({key.lower(): value for key, value in attrs.items()})
    return props


def _definition(raw, default_kind="auto"):
    empty = ("star", 1.0) if default_kind == "star" else ("auto", 0)
    if raw is None:
        return empty
    text = str(raw).strip()
    if not text:
        return empty
    if text.lower() == "auto":
        return ("auto", 0)
    if text.endswith("*"):
        weight = text[:-1].strip()
        return ("star", float(weight) if weight else 1.0)
    return ("fixed", parse_length(text, allow_percent=False, allow_auto=False))


def _parse_defs(xml_el, item_tag, size_attr, default_kind):
    defs = []
    for child in xml_el:
        name = local_name(child.tag)
        if not name:
            continue
        if name != item_tag:
            raise DslError(f"unexpected <{name}> inside <{local_name(xml_el.tag)}>")
        defs.append(_definition(child.get(size_attr), default_kind))
    return defs


def _element(xml_el, parent, ctx):
    tag = local_name(xml_el.tag)
    attrs = _attrs(xml_el)
    props = _resolve_props(tag, attrs, parent, ctx)
    node = Element(tag, props, line=xml_el.sourceline)
    if parent is not None:
        parent.add(node)

    if tag in TEXT_TAGS:
        node.runs = _collect_runs(xml_el, props, ctx)
        node.text = node.text_content()
        return node

    if tag == "Grid":
        rows = []
        cols = []
        for child in xml_el:
            name = local_name(child.tag)
            if name == "Grid.RowDefinitions":
                rows.extend(_parse_defs(child, "RowDefinition", "Height", "auto"))
            elif name == "Grid.ColumnDefinitions":
                cols.extend(_parse_defs(child, "ColumnDefinition", "Width", "auto"))
        node.meta["row_defs"] = rows
        node.meta["col_defs"] = cols

    if tag == "Table":
        columns = []
        for child in xml_el:
            name = local_name(child.tag)
            if name == "Table.Columns":
                for column in child:
                    if local_name(column.tag) != "Column":
                        raise DslError(f"unexpected <{local_name(column.tag)}> inside <Table.Columns>")
                    columns.append(_definition(column.get("Width"), "auto"))
        node.meta["columns"] = columns

    for child in xml_el:
        name = local_name(child.tag)
        if name in _SKIP_TAGS or not name:
            continue
        if tag == "Grid" and name in {"RowDefinition", "ColumnDefinition"}:
            continue
        if tag in TEXT_TAGS:
            continue
        if tag == "Table":
            _table_child(node, child, ctx)
            continue
        if tag == "Chart":
            _chart_child(node, child, ctx)
            continue
        if tag == "List":
            if name != "Item":
                raise DslError(f"unexpected <{name}> inside <List>")
            item = _element(child, node, ctx)
            item.runs = _collect_runs(child, item.props, ctx)
            continue
        if name not in VISUAL_TAGS:
            raise DslError(f"unknown element <{name}>", line=xml_el.sourceline)
        _element(child, node, ctx)

    if tag == "List":
        pass
    if tag in {"Rectangle", "Ellipse", "RoundedRectangle", "Image", "Chart"}:
        if node.children:
            raise DslError(f"<{tag}> cannot contain layout children")
    return node


def _table_child(node, xml_el, ctx):
    name = local_name(xml_el.tag)
    if name == "Row":
        row = Element("Row", _resolve_props("Row", _attrs(xml_el), node, ctx), line=xml_el.sourceline)
        node.add(row)
        for cell_el in xml_el:
            if local_name(cell_el.tag) != "Cell":
                raise DslError(f"unexpected <{local_name(cell_el.tag)}> inside <Row>")
            cell = _element(cell_el, row, ctx)
            cell.runs = _collect_runs(cell_el, cell.props, ctx)
    elif name == "Table.Rows":
        for row_el in xml_el:
            _table_child(node, row_el, ctx)
    else:
        raise DslError(f"unexpected <{name}> inside <Table>")


def _chart_child(node, xml_el, ctx):
    name = local_name(xml_el.tag)
    if name == "Category":
        node.meta.setdefault("categories", []).append(_clean(xml_el.text))
    elif name == "Series":
        attrs = _attrs(xml_el)
        raw = attrs.get("Values") or _clean(xml_el.text)
        values = []
        for part in re.split(r"[,;\s]+", str(raw)):
            if not part:
                continue
            try:
                values.append(float(part))
            except ValueError as exc:
                raise DslError(f"invalid chart value {part!r}") from exc
        node.meta.setdefault("series", []).append(
            {
                "name": attrs.get("Name", f"Series {len(node.meta.get('series', [])) + 1}"),
                "values": values,
                "color": _color(attrs.get("Color"), ctx),
            }
        )
    else:
        raise DslError(f"unexpected <{name}> inside <Chart>")


def _load(source, source_name):
    if isinstance(source, bytes):
        return source, source_name
    if isinstance(source, os.PathLike):
        path = Path(source)
        return path.read_bytes(), str(path)
    text = str(source)
    if "<" in text and ">" in text:
        return text.encode("utf-8"), source_name
    path = Path(text)
    return path.read_bytes(), str(path)


def _resolve_image(node, ctx):
    source = node.get("Source")
    if not source:
        raise DslError("Image requires Source", element=node)
    path = Path(source)
    if not path.is_absolute():
        path = ctx.base_dir / path
    if not path.exists():
        raise DslError(f"image not found: {source}", element=node)
    node.meta["path"] = str(path)
    try:
        from PIL import Image

        with Image.open(path) as image:
            width, height = image.size
    except Exception as exc:
        raise DslError(f"cannot read image {source}: {exc}", element=node) from exc
    node.meta["pixel_size"] = (width, height)
    node.meta["intrinsic"] = (width * 9525, height * 9525)


def parse_deck(source, source_name=None):
    data, name = _load(source, source_name)
    try:
        root = etree.fromstring(data, parser=SAFE_PARSER)
    except etree.XMLSyntaxError as exc:
        raise DslError(f"XML parse error: {exc}", source=name) from exc

    try:
        return _parse_root(root, name)
    except DslError as exc:
        if not exc.source and name:
            exc.source = name
            exc.args = (exc.describe(),)
        raise


def _parse_root(root, name):
    if local_name(root.tag) != "Deck":
        raise DslError(f"root element must be <Deck>, got <{local_name(root.tag)}>", line=root.sourceline)

    deck_attrs = _attrs(root)
    width = parse_length(deck_attrs["Width"]) if "Width" in deck_attrs else 12192000
    height = parse_length(deck_attrs["Height"]) if "Height" in deck_attrs else 6858000

    theme = Theme()
    styles = {}
    implicit = {}
    named_colors = {}
    meta = {}

    theme_el = None
    styles_el = None
    for child in root:
        child_name = local_name(child.tag)
        if child_name == "Theme":
            theme_el = child
        elif child_name == "Styles":
            styles_el = child
        elif child_name == "Meta":
            meta = {
                key: value
                for key, value in _attrs(child).items()
                if key.lower() not in {"xmlns", "schemaLocation"}
            }
        elif child_name != "Slide" and child_name:
            raise DslError(f"unknown element <{child_name}> in <Deck>", line=child.sourceline)

    if theme_el is not None:
        theme_attrs = _attrs(theme_el)
        theme.major_latin = theme_attrs.get("MajorFont", theme.major_latin)
        theme.major_ea = theme_attrs.get("MajorEastAsianFont", theme.major_ea)
        theme.minor_latin = theme_attrs.get("MinorFont", theme.minor_latin)
        theme.minor_ea = theme_attrs.get("MinorEastAsianFont", theme.minor_ea)
        for color_el in theme_el:
            if local_name(color_el.tag) != "Color":
                raise DslError("only <Color> is allowed in <Theme>", line=color_el.sourceline)
            key = _attrs(color_el).get("Key")
            value = _attrs(color_el).get("Value")
            if not key or not value:
                raise DslError("<Color> requires Key and Value", line=color_el.sourceline)
            theme.colors[str(key)] = parse_color(value).value

    if styles_el is not None:
        for child in styles_el:
            child_name = local_name(child.tag)
            if child_name == "Color":
                attrs = _attrs(child)
                key = attrs.get("Key")
                value = attrs.get("Value")
                if not key or not value:
                    raise DslError("<Color> requires Key and Value", element=None, line=child.sourceline)
                named_colors[str(key)] = parse_color(value, named_colors)
            elif child_name == "Style":
                attrs = _attrs(child)
                key = attrs.pop("Key", None)
                attrs.pop("TargetType", None)
                if key:
                    styles[str(key)] = attrs
                else:
                    target = _attrs(child).get("TargetType")
                    if not target:
                        raise DslError("<Style> requires Key or TargetType", line=child.sourceline)
                    implicit[str(target)] = attrs
            else:
                raise DslError(f"unknown element <{child_name}> in <Styles>", line=child.sourceline)

    ctx = Context(theme, _defaults(theme), implicit, styles, named_colors, name)
    root_props = _resolve_props("Deck", deck_attrs, None, ctx)
    deck_root = Element("Deck", root_props, line=root.sourceline)

    deck = Deck(width=width, height=height, theme=theme, root=deck_root, meta=meta, named_colors=named_colors, source=name)

    for child in root:
        if local_name(child.tag) != "Slide":
            continue
        slide = _element(child, deck_root, ctx)
        if not slide.get("Layout"):
            slide.props["layout"] = "Blank"
        deck.slides.append(slide)

    if not deck.slides:
        raise DslError("deck has no <Slide>", source=name)

    for slide in deck.slides:
        _prepare_tree(slide, ctx)

    return deck


def _prepare_tree(node, ctx):
    prepare(node)
    for child in node.children:
        if child.tag in {"Row", "Cell", "Item"}:
            prepare(child)
            for grand in child.children:
                _prepare_tree(grand, ctx)
            continue
        if child.tag == "Image":
            _resolve_image(child, ctx)
        prepare(child)
        _prepare_tree(child, ctx)
