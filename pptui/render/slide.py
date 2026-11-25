from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
from pptx.util import Emu

from ..errors import DslError
from ..model import Deck
from . import chart as chart_render
from . import image as image_render
from . import shapes as shapes_render
from . import table as table_render
from . import text as text_render
from .xmlutil import BGPR_TAIL, drop_style, set_fill, set_shape_fill, set_shape_line

CONTAINERS = {"Canvas", "StackPanel", "Grid", "Border", "DockPanel"}

DEFAULT_TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "base.pptx"


class RenderContext:
    def __init__(self, deck, metrics=None):
        self.deck = deck
        self.metrics = metrics

    def color(self, el, name):
        return el.get_color(name, self.deck.named_colors)


def render_element(shapes, el, ctx):
    tag = el.tag
    if tag == "TextBlock":
        text_render.render_text(shapes, el, ctx)
    elif tag == "List":
        text_render.render_list(shapes, el, ctx)
    elif tag in shapes_render.SHAPES:
        shapes_render.render_shape(shapes, el, ctx)
    elif tag == "Image":
        image_render.render_image(shapes, el, ctx)
    elif tag == "Table":
        table_render.render_table(shapes, el, ctx)
    elif tag == "Chart":
        chart_render.render_chart(shapes, el, ctx)
    elif tag in CONTAINERS:
        _paint_container(shapes, el, ctx)
        for child in el.children:
            render_element(shapes, child, ctx)


def _paint_container(shapes, el, ctx):
    background = ctx.color(el, "Background")
    stroke = ctx.color(el, "BorderBrush")
    if background is None and stroke is None:
        return
    radius = el.get_length("RadiusX") if el.tag == "Border" else None
    rounded = isinstance(radius, int) and radius > 0
    shape = shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
        Emu(el.rect.x),
        Emu(el.rect.y),
        Emu(el.rect.w),
        Emu(el.rect.h),
    )
    drop_style(shape)
    set_shape_fill(shape, background)
    if stroke is not None:
        width = el.get_length("BorderThickness") or 12700
        set_shape_line(shape, stroke, width)
    else:
        set_shape_line(shape, None)
    if rounded:
        shape.adjustments[0] = min(0.5, 2.0 * radius / max(1, min(el.rect.w, el.rect.h)))


def render_deck(deck: Deck, metrics=None):
    prs = Presentation(_template(deck))
    prs.slide_width = Emu(deck.width)
    prs.slide_height = Emu(deck.height)
    _set_core_properties(prs, deck)
    ctx = RenderContext(deck, metrics)
    for slide_el in deck.slides:
        layout = _layout(prs, slide_el.get("Layout", "Blank"))
        slide = prs.slides.add_slide(layout)
        background = ctx.color(slide_el, "Background")
        if background is not None:
            _background(slide, background)
        for child in slide_el.children:
            render_element(slide.shapes, child, ctx)
        notes = slide_el.get("Notes")
        if notes:
            slide.notes_slide.notes_text_frame.text = str(notes)
    return prs


def _template(deck):
    raw = deck.root.get("Template")
    if raw:
        path = Path(str(raw))
        if not path.is_absolute() and deck.source:
            path = Path(deck.source).resolve().parent / path
        if not path.exists():
            raise DslError(f"template not found: {raw}")
        return str(path)
    if DEFAULT_TEMPLATE.exists():
        return str(DEFAULT_TEMPLATE)
    return None


def _layout(prs, name):
    target = str(name).strip().lower()
    for layout in prs.slide_layouts:
        if layout.name.strip().lower() == target:
            return layout
    for layout in prs.slide_layouts:
        if layout.name.strip().lower() == "blank":
            return layout
    return prs.slide_layouts[-1]


def _background(slide, color):
    slide.background.fill.solid()
    if color.kind == "scheme":
        cSld = slide._element.find(qn("p:cSld"))
        bgPr = cSld.find(qn("p:bg")).find(qn("p:bgPr"))
        set_fill(bgPr, color, BGPR_TAIL)
    else:
        slide.background.fill.fore_color.rgb = RGBColor.from_string(color.value)


def _set_core_properties(prs, deck):
    props = prs.core_properties
    mapping = {
        "title": "Title",
        "author": "Author",
        "subject": "Subject",
        "keywords": "Keywords",
        "comments": "Comments",
        "category": "Category",
    }
    for attr, key in mapping.items():
        value = deck.meta.get(key)
        if value:
            setattr(props, attr, value)
