from __future__ import annotations

from pptx.enum.text import MSO_ANCHOR
from pptx.util import Emu

from .text import fill_frame
from .xmlutil import TCPR_TAIL, set_cell_borders, set_fill

ANCHORS = {
    "top": MSO_ANCHOR.TOP,
    "center": MSO_ANCHOR.MIDDLE,
    "middle": MSO_ANCHOR.MIDDLE,
    "bottom": MSO_ANCHOR.BOTTOM,
}


def render_table(shapes, el, ctx):
    rows = el.children
    widths = list(el.meta.get("table_widths") or [])
    heights = list(el.meta.get("table_heights") or [])
    columns = len(widths) or max((len(row.children) for row in rows), default=1)
    if not widths:
        widths = [max(1, el.rect.w // columns)] * columns

    graphic = shapes.add_table(len(rows), columns, Emu(el.rect.x), Emu(el.rect.y), Emu(el.rect.w), Emu(el.rect.h))
    table = graphic.table
    table.first_row = False
    table.first_col = False
    table.last_row = False
    table.last_col = False
    table.horz_banding = False
    table.vert_banding = False

    _apply_sizes(table, widths, heights, el.rect)

    padding = el.meta.get("cell_padding", int(0.08 * 914400))
    border_color = ctx.color(el, "BorderBrush")
    border_width = el.get_length("BorderThickness") or 0
    covered = set()
    for row_index, row in enumerate(rows):
        for column_index, cell_el in enumerate(row.children):
            row_span = _span(cell_el, "RowSpan")
            col_span = _span(cell_el, "ColSpan")
            if row_span > 1 or col_span > 1:
                target_row = min(len(rows) - 1, row_index + row_span - 1)
                target_col = min(columns - 1, column_index + col_span - 1)
                table.cell(row_index, column_index).merge(table.cell(target_row, target_col))
                for rr in range(row_index, target_row + 1):
                    for cc in range(column_index, target_col + 1):
                        if (rr, cc) != (row_index, column_index):
                            covered.add((rr, cc))

    for row_index, row in enumerate(rows):
        for column_index, cell_el in enumerate(row.children):
            if (row_index, column_index) in covered:
                continue
            cell = table.cell(row_index, column_index)
            cell_padding = cell_el.get_length("Padding")
            pad = cell_padding if isinstance(cell_padding, int) else padding
            anchor_name = str(cell_el.get("VerticalAlignment") or el.get("VerticalAlignment", "Center")).lower()
            cell.vertical_anchor = ANCHORS.get(anchor_name, MSO_ANCHOR.MIDDLE)
            background = ctx.color(cell_el, "Background")
            if background is None:
                cell.fill.background()
            else:
                set_fill(cell._tc.get_or_add_tcPr(), background, TCPR_TAIL)
            cell_border = ctx.color(cell_el, "BorderBrush") or border_color
            cell_width = cell_el.get_length("BorderThickness") or border_width
            if cell_border is not None and cell_width:
                set_cell_borders(cell._tc, cell_border, cell_width)
            fill_frame(cell.text_frame, cell_el, ctx, anchor=anchor_name)
            cell.margin_left = Emu(pad)
            cell.margin_right = Emu(pad)
            cell.margin_top = Emu(pad)
            cell.margin_bottom = Emu(pad)


def _apply_sizes(table, widths, heights, rect):
    total_w = sum(widths) or rect.w
    scale_w = rect.w / total_w if total_w else 1.0
    for index, width in enumerate(widths[: len(table.columns)]):
        table.columns[index].width = Emu(max(1, int(width * scale_w)))
    total_h = sum(heights) or rect.h
    scale_h = rect.h / total_h if total_h else 1.0
    for index, height in enumerate(heights[: len(table.rows)]):
        table.rows[index].height = Emu(max(1, int(height * scale_h)))


def _span(cell_el, name):
    try:
        return max(1, int(str(cell_el.get(name, 1)).strip()))
    except ValueError:
        return 1
