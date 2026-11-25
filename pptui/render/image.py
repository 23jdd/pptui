from __future__ import annotations

from pptx.util import Emu


def render_image(shapes, el, ctx):
    path = el.meta.get("path")
    intrinsic_w, intrinsic_h = el.meta.get("intrinsic", (0, 0))
    rect = el.rect
    stretch = str(el.get("Stretch", "Uniform")).strip().lower()

    if stretch == "fill" or intrinsic_w <= 0 or intrinsic_h <= 0:
        shapes.add_picture(path, Emu(rect.x), Emu(rect.y), Emu(rect.w), Emu(rect.h))
        return

    if stretch == "none":
        width, height = intrinsic_w, intrinsic_h
        left = rect.x + (rect.w - width) // 2
        top = rect.y + (rect.h - height) // 2
        shapes.add_picture(path, Emu(left), Emu(top), Emu(width), Emu(height))
        return

    if stretch == "uniformtofill":
        picture = shapes.add_picture(path, Emu(rect.x), Emu(rect.y), Emu(rect.w), Emu(rect.h))
        scale = max(rect.w / intrinsic_w, rect.h / intrinsic_h)
        drawn_w = intrinsic_w * scale
        drawn_h = intrinsic_h * scale
        crop_x = max(0.0, (drawn_w - rect.w) / (2.0 * drawn_w))
        crop_y = max(0.0, (drawn_h - rect.h) / (2.0 * drawn_h))
        picture.crop_left = crop_x
        picture.crop_right = crop_x
        picture.crop_top = crop_y
        picture.crop_bottom = crop_y
        return

    scale = min(rect.w / intrinsic_w, rect.h / intrinsic_h)
    width = max(1, int(intrinsic_w * scale))
    height = max(1, int(intrinsic_h * scale))
    left = rect.x + (rect.w - width) // 2
    top = rect.y + (rect.h - height) // 2
    shapes.add_picture(path, Emu(left), Emu(top), Emu(width), Emu(height))
