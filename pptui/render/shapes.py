from __future__ import annotations

from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Emu

from .xmlutil import drop_style, set_shape_fill, set_shape_line

SHAPES = {
    "Rectangle": MSO_SHAPE.RECTANGLE,
    "Ellipse": MSO_SHAPE.OVAL,
    "RoundedRectangle": MSO_SHAPE.ROUNDED_RECTANGLE,
}


def render_shape(shapes, el, ctx):
    shape = shapes.add_shape(SHAPES[el.tag], Emu(el.rect.x), Emu(el.rect.y), Emu(el.rect.w), Emu(el.rect.h))
    drop_style(shape)
    fill = el.get("Fill")
    fill_color = None if fill is None or str(fill).strip().lower() in ("none", "transparent") else ctx.color(el, "Fill")
    set_shape_fill(shape, fill_color)
    _apply_stroke(shape, el, ctx)
    if el.tag == "RoundedRectangle":
        radius = el.get_length("RadiusX")
        if isinstance(radius, int) and radius > 0:
            shape.adjustments[0] = min(0.5, 2.0 * radius / max(1, min(el.rect.w, el.rect.h)))


def apply_stroke(shape, el, ctx):
    _apply_stroke(shape, el, ctx)


def _apply_stroke(shape, el, ctx):
    stroke = el.get("Stroke")
    if stroke is None or str(stroke).strip().lower() in ("none", "transparent"):
        set_shape_line(shape, None)
        return
    color = ctx.color(el, "Stroke")
    thickness = el.get_length("StrokeThickness")
    width = thickness if isinstance(thickness, int) else 12700
    set_shape_line(shape, color, width or 12700)
