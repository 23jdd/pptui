from __future__ import annotations

from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.util import Emu, Pt

from ..metrics import is_cjk
from ..model import split_runs
from .xmlutil import set_bullet, set_norm_autofit, set_run_color, set_run_fonts

_ALIGN = {
    "left": PP_ALIGN.LEFT,
    "center": PP_ALIGN.CENTER,
    "right": PP_ALIGN.RIGHT,
    "justify": PP_ALIGN.JUSTIFY,
}

_ANCHOR = {
    "top": MSO_ANCHOR.TOP,
    "center": MSO_ANCHOR.MIDDLE,
    "middle": MSO_ANCHOR.MIDDLE,
    "bottom": MSO_ANCHOR.BOTTOM,
}


def write_runs(paragraph, runs):
    if not runs:
        paragraph.add_run().text = ""
        return
    for run in runs:
        piece = paragraph.add_run()
        piece.text = run.text
        font = piece.font
        font.size = Pt(run.size)
        font.bold = run.bold
        font.italic = run.italic
        if run.underline:
            font.underline = True
        rPr = piece._r.get_or_add_rPr()
        set_run_color(rPr, run.color)
        set_run_fonts(rPr, run.family, run.ea)
        if run.spacing:
            rPr.set("spc", str(int(round(run.spacing * 100))))


def fill_frame(tf, el, ctx, alignment=None, anchor=None):
    tf.word_wrap = str(el.get("TextWrapping", "Wrap")).lower() != "nowrap"
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = Emu(el.padding.left)
    tf.margin_right = Emu(el.padding.right)
    tf.margin_top = Emu(el.padding.top)
    tf.margin_bottom = Emu(el.padding.bottom)
    anchor_name = str(anchor or el.get("VerticalContentAlignment", "Top")).lower()
    tf.vertical_anchor = _ANCHOR.get(anchor_name, MSO_ANCHOR.TOP)
    align_name = str(alignment or el.get("TextAlignment", "Left")).lower()
    align = _ALIGN.get(align_name, PP_ALIGN.LEFT)
    line_height = _line_height(el)
    paragraphs = split_runs(el.runs)
    for index, runs in enumerate(paragraphs):
        paragraph = tf.paragraphs[0] if index == 0 else tf.add_paragraph()
        paragraph.alignment = align
        if line_height:
            paragraph.line_spacing = Pt(line_height)
        paragraph.space_before = Pt(0)
        paragraph.space_after = Pt(0)
        write_runs(paragraph, runs)


def render_text(shapes, el, ctx):
    box = shapes.add_textbox(Emu(el.rect.x), Emu(el.rect.y), Emu(el.rect.w), Emu(el.rect.h))
    fill_frame(box.text_frame, el, ctx)
    _apply_shrink(box.text_frame, el, ctx)


def render_list(shapes, el, ctx):
    box = shapes.add_textbox(Emu(el.rect.x), Emu(el.rect.y), Emu(el.rect.w), Emu(el.rect.h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = Emu(el.padding.left)
    tf.margin_right = Emu(el.padding.right)
    tf.margin_top = Emu(el.padding.top)
    tf.margin_bottom = Emu(el.padding.bottom)
    tf.vertical_anchor = _ANCHOR.get(str(el.get("VerticalContentAlignment", "Top")).lower(), MSO_ANCHOR.TOP)
    align = _ALIGN.get(str(el.get("TextAlignment", "Left")).lower(), PP_ALIGN.LEFT)
    indent = el.meta.get("indent", int(0.3 * 914400))
    spacing = el.get_length("ItemSpacing")
    spacing_pt = Emu(spacing) if isinstance(spacing, int) else Pt(6)
    bullet = str(el.get("Bullet", "Disc"))
    line_height = _line_height(el)
    for index, item in enumerate(el.children):
        paragraph = tf.paragraphs[0] if index == 0 else tf.add_paragraph()
        paragraph.alignment = align
        if line_height:
            paragraph.line_spacing = Pt(line_height)
        paragraph.space_before = Pt(0)
        paragraph.space_after = spacing_pt
        level = _level(item)
        bullets = _bullet_spec(bullet)
        set_bullet(paragraph._p.get_or_add_pPr(), bullets[0], bullets[1], indent * (level + 1), -indent)
        write_runs(paragraph, item.runs)
    _apply_shrink(box.text_frame, el, ctx)


def _bullet_spec(value):
    text = str(value).strip()
    if text.lower() in ("none", "false", ""):
        return None, False
    if text.lower() in ("number", "numbered", "arabic"):
        return None, True
    mapping = {"disc": "•", "circle": "○", "square": "▪", "dash": "–"}
    return mapping.get(text.lower(), text), False


def _level(item):
    try:
        return max(0, int(str(item.get("Level", 0)).strip()))
    except ValueError:
        return 0


def _line_height(el):
    raw = el.get("LineHeight")
    if raw is None:
        return None
    text = str(raw).strip().lower()
    try:
        if text.endswith("pt"):
            return float(text[:-2])
        if text.endswith("px"):
            return float(text[:-2]) * 0.75
        return float(text)
    except ValueError:
        return None


def _apply_shrink(tf, el, ctx):
    mode = str(el.get("AutoFit", "Shrink")).lower()
    if mode != "shrink":
        return
    pad = el.padding
    content_h = el.measured.h - pad.vertical
    box_h = el.rect.h - pad.vertical
    box_w = el.rect.w - pad.horizontal
    if content_h <= 0 or box_h <= 0 or box_w <= 0:
        return
    scale = 1.0
    if content_h > box_h * 0.995:
        scale = min(scale, max(0.5, box_h / content_h))
    metrics = getattr(ctx, "metrics", None)
    if metrics is not None and el.runs:
        widest = _widest_token(el, metrics)
        if widest > box_w:
            scale = min(scale, max(0.4, box_w * 0.98 / widest))
    if scale < 0.995:
        set_norm_autofit(tf._txBody, scale)


def _widest_token(el, metrics):
    best = 0
    for run in el.runs:
        buffer = ""
        for ch in run.text + " ":
            if ch.isspace() or is_cjk(ch):
                if buffer:
                    best = max(best, metrics.width_emu(buffer, run.family, run.size, run.bold, run.italic, ea=run.ea))
                    buffer = ""
                if ch.isspace():
                    continue
                best = max(best, metrics.width_emu(ch, run.family, run.size, run.bold, run.italic, ea=run.ea))
            else:
                buffer += ch
    return best
