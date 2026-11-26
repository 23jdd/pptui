from __future__ import annotations

from .errors import DslError
from .metrics import FontMetrics
from .model import Element, prepare
from .textlayout import measure_runs
from .units import AUTO, INF, Percent, Rect, Size, Thickness, parse_length, parse_thickness, resolve_length

PT = 12700


def _sub(value, amount):
    if value >= INF:
        return INF
    return max(0, value - amount)


def _align_offset(align, outer, inner):
    if inner >= outer:
        return 0
    if align == "center":
        return (outer - inner) // 2
    if align == "right" or align == "bottom":
        return outer - inner
    return 0


class LayoutEngine:
    def __init__(self, deck):
        self.deck = deck
        self.metrics = FontMetrics()
        self.page = Size(deck.width, deck.height)

    def run(self):
        for slide in self.deck.slides:
            prepare(slide)
            slide.rect = Rect(0, 0, self.page.w, self.page.h)
            self._layout_slide(slide)
        return self

    def _layout_slide(self, slide):
        if not slide.children:
            return
        for child in slide.children:
            self.measure(child, self.page)
            self.arrange(child, Rect(0, 0, self.page.w, self.page.h))

    def measure(self, el, avail):
        prepare(el)
        margin = el.margin
        inner = Size(_sub(avail.w, margin.horizontal), _sub(avail.h, margin.vertical))
        # An explicit Width/Height constrains the content as well: a 1in-wide
        # TextBlock must wrap at 1in, not at whatever width the parent offered.
        given_w = self._size(el.width, inner.w, None)
        given_h = self._size(el.height, inner.h, None)
        content_avail = Size(
            inner.w if given_w is None else min(inner.w, given_w),
            inner.h if given_h is None else min(inner.h, given_h),
        )
        content = self._measure_content(el, content_avail)
        width = content.w if given_w is None else given_w
        height = content.h if given_h is None else given_h
        width = self._clamp(width, el.min_width, el.max_width, inner.w)
        height = self._clamp(height, el.min_height, el.max_height, inner.h)
        el.measured = Size(int(width), int(height))
        return Size(int(width + margin.horizontal), int(height + margin.vertical))

    def _size(self, value, base, fallback):
        if value is None or value is AUTO:
            return fallback
        if isinstance(value, Percent):
            if base >= INF:
                return fallback
            return int(round(base * value.value))
        return int(value)

    def _clamp(self, value, low, high, base):
        if low is not None and low is not AUTO:
            value = max(value, self._size(low, base, 0))
        if high is not None and high is not AUTO:
            value = min(value, self._size(high, base, value))
        return value

    def _measure_content(self, el, avail):
        tag = el.tag
        if tag == "TextBlock":
            return self._measure_text(el, avail.w)
        if tag == "List":
            return self._measure_list(el, avail.w)
        if tag == "Canvas":
            for child in el.children:
                self.measure(child, Size(INF, INF))
            return Size(0, 0)
        if tag == "StackPanel":
            return self._measure_stack(el, avail)
        if tag == "Grid":
            return self._measure_grid(el, avail)
        if tag == "Border":
            return self._measure_border(el, avail)
        if tag == "DockPanel":
            return self._measure_dock(el, avail)
        if tag == "Image":
            intrinsic = el.meta.get("intrinsic", (0, 0))
            return Size(intrinsic[0], intrinsic[1])
        if tag == "Table":
            return self._measure_table(el, avail)
        if tag == "Chart":
            return Size(avail.w if avail.w < INF else 0, int((avail.w if avail.w < INF else 0) * 0.6))
        return Size(0, 0)

    def _measure_text(self, el, avail_w):
        wrap = str(el.get("TextWrapping", "Wrap")).lower() != "nowrap"
        line_height = _float_or_none(el.get("LineHeight"))
        pad = el.padding
        inner_w = max(1, avail_w - pad.horizontal) if avail_w < INF else avail_w
        stats = {}
        size = measure_runs(
            el.runs, inner_w, self.metrics, wrap=wrap,
            line_height_pt=line_height, stats=stats,
        )
        # Remember whether the text actually needed more than one line: an
        # auto-sized box is exactly as wide as its text, so if PowerPoint lays
        # the text out a hair wider it would re-wrap. Renderers use this flag
        # to switch such boxes to `wrap="none"`.
        el.meta["wrapped"] = stats.get("wrapped", False)
        return Size(size.w + pad.horizontal, size.h + pad.vertical)

    def _measure_list(self, el, avail_w):
        indent = self._length(el, "Indent", int(0.3 * 914400))
        spacing = self._length(el, "ItemSpacing", int(6 * PT))
        line_height = _float_or_none(el.get("LineHeight"))
        pad = el.padding
        inner_w = max(1, avail_w - pad.horizontal) if avail_w < INF else avail_w
        total = 0
        widest = 0
        for item in el.children:
            size = measure_runs(item.runs, max(1, inner_w - indent), self.metrics, wrap=True, line_height_pt=line_height)
            total += size.h + spacing
            widest = max(widest, size.w + indent)
        if el.children:
            total -= spacing
        el.meta["indent"] = indent
        return Size(widest + pad.horizontal, total + pad.vertical)

    def _measure_stack(self, el, avail):
        horizontal = str(el.get("Orientation", "Vertical")).lower().startswith("h")
        spacing = self._length(el, "Spacing", 0)
        main = 0
        cross = 0
        for index, child in enumerate(el.children):
            child_avail = Size(INF, avail.h) if horizontal else Size(avail.w, INF)
            size = self.measure(child, child_avail)
            if index:
                main += spacing
            main += size.w if horizontal else size.h
            cross = max(cross, size.h if horizontal else size.w)
        return Size(main, cross) if horizontal else Size(cross, main)

    def _measure_border(self, el, avail):
        pad = el.padding
        border = self._thickness(el, "BorderThickness")
        inner = Size(_sub(avail.w, pad.horizontal + border.horizontal), _sub(avail.h, pad.vertical + border.vertical))
        child_size = Size(0, 0)
        if el.children:
            child_size = self.measure(el.children[0], inner)
        return Size(child_size.w + pad.horizontal + border.horizontal, child_size.h + pad.vertical + border.vertical)

    def _measure_dock(self, el, avail):
        remaining = Size(avail.w, avail.h)
        widths = 0
        heights = 0
        for child in el.children:
            size = self.measure(child, remaining)
            dock = str(child.get("DockPanel.Dock", "Left")).lower()
            if dock in ("top", "bottom"):
                heights += size.h
                widths = max(widths, size.w)
                remaining = Size(remaining.w, _sub(remaining.h, size.h))
            else:
                widths += size.w
                heights = max(heights, size.h)
                remaining = Size(_sub(remaining.w, size.w), remaining.h)
        return Size(widths, heights)

    def _measure_grid(self, el, avail):
        col_defs = el.meta.get("col_defs") or [("star", 1.0)]
        row_defs = el.meta.get("row_defs") or [("star", 1.0)]
        widths = self._axis_sizes(col_defs, avail.w, el, "column", avail.h)
        heights = self._axis_sizes(row_defs, avail.h, el, "row", avail.w, widths)
        for child in el.children:
            self.measure(child, self._cell_size(child, widths, heights))
        el.meta["grid"] = (widths, heights)
        return Size(sum(widths), sum(heights))

    def _cell_size(self, child, widths, heights):
        column = _int(child.get("Grid.Column", 0))
        row = _int(child.get("Grid.Row", 0))
        colspan = max(1, _int(child.get("Grid.ColumnSpan", 1)))
        rowspan = max(1, _int(child.get("Grid.RowSpan", 1)))
        width = sum(widths[column:column + colspan]) if column < len(widths) else 0
        height = sum(heights[row:row + rowspan]) if row < len(heights) else 0
        return Size(width, height)

    def _axis_sizes(self, defs, total, el, axis, cross, widths=None):
        sizes = [0] * len(defs)
        stars = []
        autos = []
        used = 0
        for index, (kind, value) in enumerate(defs):
            if kind == "fixed":
                sizes[index] = int(value)
                used += sizes[index]
            elif kind == "star":
                stars.append(index)
            else:
                autos.append(index)
        for index in autos:
            sizes[index] = self._auto_size(el, index, axis, cross, widths)
            used += sizes[index]
        remaining = max(0, total - used) if total < INF else 0
        if stars:
            weights = [max(0.0, float(defs[index][1] or 1.0)) for index in stars]
            weight_sum = sum(weights) or 1.0
            assigned = 0
            for position, index in enumerate(stars):
                part = int(remaining * weights[position] / weight_sum)
                sizes[index] = part
                assigned += part
            if assigned != remaining:
                sizes[stars[-1]] += remaining - assigned
        return sizes

    def _auto_size(self, el, index, axis, cross, widths):
        best = 0
        for child in el.children:
            if axis == "column":
                if _int(child.get("Grid.Column", 0)) != index:
                    continue
                if max(1, _int(child.get("Grid.ColumnSpan", 1))) != 1:
                    continue
                size = self.measure(child, Size(INF, cross if cross < INF else INF))
                best = max(best, size.w)
            else:
                if _int(child.get("Grid.Row", 0)) != index:
                    continue
                if max(1, _int(child.get("Grid.RowSpan", 1))) != 1:
                    continue
                column = _int(child.get("Grid.Column", 0))
                span = max(1, _int(child.get("Grid.ColumnSpan", 1)))
                cell_w = sum(widths[column:column + span]) if widths else cross
                size = self.measure(child, Size(cell_w, INF))
                best = max(best, size.h)
        return best

    def _measure_table(self, el, avail):
        columns = list(el.meta.get("columns") or [])
        rows = el.children
        count = len(columns) or max((len(row.children) for row in rows), default=1)
        if not columns:
            columns = [("star", 1.0)] * count
        padding = self._length(el, "CellPadding", int(0.08 * 914400))
        widths = self._table_widths(columns, avail.w, el, padding)
        heights = []
        for row in rows:
            fixed = row.get_length("Height")
            if fixed is not None and fixed is not AUTO:
                heights.append(resolve_length(fixed, avail.h, 0))
                continue
            height = 0
            for index, cell in enumerate(row.children):
                span = max(1, _int(cell.get("ColSpan", 1)))
                cell_w = sum(widths[index:index + span]) if index < len(widths) else avail.w
                cell_padding = cell.get_length("Padding")
                pad = cell_padding if isinstance(cell_padding, int) else padding
                wrap = str(cell.get("TextWrapping", "Wrap")).lower() != "nowrap"
                size = measure_runs(cell.runs, max(1, cell_w - 2 * pad), self.metrics, wrap=wrap)
                height = max(height, size.h + 2 * pad)
            heights.append(height)
        el.meta["table_widths"] = widths
        el.meta["table_heights"] = heights
        el.meta["cell_padding"] = padding
        return Size(sum(widths), sum(heights))

    def _table_widths(self, columns, total, el, padding):
        widths = [0] * len(columns)
        stars = []
        used = 0
        for index, (kind, value) in enumerate(columns):
            if kind == "fixed":
                widths[index] = int(value)
                used += widths[index]
            elif kind == "star":
                stars.append(index)
            else:
                widths[index] = self._auto_column_width(el, index, padding)
                used += widths[index]
        remaining = max(0, total - used) if total < INF else 0
        if stars:
            weights = [max(0.0, float(columns[index][1] or 1.0)) for index in stars]
            weight_sum = sum(weights) or 1.0
            assigned = 0
            for position, index in enumerate(stars):
                part = int(remaining * weights[position] / weight_sum)
                widths[index] = part
                assigned += part
            if assigned != remaining:
                widths[stars[-1]] += remaining - assigned
        return widths

    def _auto_column_width(self, el, index, padding):
        best = 0
        for row in el.children:
            for column, cell in enumerate(row.children):
                if column != index:
                    continue
                size = measure_runs(cell.runs, INF, self.metrics, wrap=False)
                best = max(best, size.w + 2 * padding)
        return best

    def arrange(self, el, slot):
        prepare(el)
        margin = el.margin
        inner = Rect(
            slot.x + margin.left,
            slot.y + margin.top,
            max(0, slot.w - margin.horizontal),
            max(0, slot.h - margin.vertical),
        )
        width = el.measured.w
        height = el.measured.h
        if el.halign == "stretch" and (el.width is None or el.width is AUTO):
            width = inner.w
        else:
            width = min(width, inner.w)
        if el.valign == "stretch" and (el.height is None or el.height is AUTO):
            height = inner.h
        else:
            height = min(height, inner.h)
        x = inner.x + _align_offset(el.halign, inner.w, width)
        y = inner.y + _align_offset(el.valign, inner.h, height)
        el.rect = Rect(x, y, width, height)
        self._arrange_content(el, el.rect)

    def _arrange_content(self, el, rect):
        tag = el.tag
        if tag == "Canvas":
            for child in el.children:
                left = self._attached(child, "Canvas.Left", 0)
                top = self._attached(child, "Canvas.Top", 0)
                size = child.measured
                self.arrange(child, Rect(rect.x + left, rect.y + top, size.w, size.h))
        elif tag == "StackPanel":
            self._arrange_stack(el, rect)
        elif tag == "Grid":
            self._arrange_grid(el, rect)
        elif tag == "Border":
            if not el.children:
                return
            pad = el.padding
            border = self._thickness(el, "BorderThickness")
            inner = rect.deflate(Thickness(pad.left + border.left, pad.top + border.top, pad.right + border.right, pad.bottom + border.bottom))
            self.arrange(el.children[0], inner)
        elif tag == "DockPanel":
            self._arrange_dock(el, rect)

    def _arrange_stack(self, el, rect):
        horizontal = str(el.get("Orientation", "Vertical")).lower().startswith("h")
        spacing = self._length(el, "Spacing", 0)
        cursor = rect.x if horizontal else rect.y
        for child in el.children:
            size = child.measured
            if horizontal:
                self.arrange(child, Rect(cursor, rect.y, size.w, rect.h))
                cursor += size.w + spacing
            else:
                self.arrange(child, Rect(rect.x, cursor, rect.w, size.h))
                cursor += size.h + spacing

    def _arrange_grid(self, el, rect):
        widths, heights = el.meta.get("grid", ([], []))
        for child in el.children:
            column = _int(child.get("Grid.Column", 0))
            row = _int(child.get("Grid.Row", 0))
            colspan = max(1, _int(child.get("Grid.ColumnSpan", 1)))
            rowspan = max(1, _int(child.get("Grid.RowSpan", 1)))
            x = rect.x + sum(widths[:column])
            y = rect.y + sum(heights[:row])
            width = sum(widths[column:column + colspan])
            height = sum(heights[row:row + rowspan])
            self.arrange(child, Rect(x, y, width, height))

    def _arrange_dock(self, el, rect):
        left, top, right, bottom = rect.x, rect.y, rect.right, rect.bottom
        last_fill = el.get_bool("LastChildFill", True)
        count = len(el.children)
        for index, child in enumerate(el.children):
            size = child.measured
            dock = str(child.get("DockPanel.Dock", "Left")).lower()
            if last_fill and index == count - 1:
                slot = Rect(left, top, max(0, right - left), max(0, bottom - top))
            elif dock in ("top", "bottom"):
                height = min(size.h, max(0, bottom - top))
                slot = Rect(left, top, max(0, right - left), height)
                if dock == "top":
                    top += height
                else:
                    slot = Rect(left, bottom - height, max(0, right - left), height)
                    bottom -= height
            else:
                width = min(size.w, max(0, right - left))
                if dock == "left":
                    slot = Rect(left, top, width, max(0, bottom - top))
                    left += width
                else:
                    slot = Rect(right - width, top, width, max(0, bottom - top))
                    right -= width
            self.arrange(child, slot)

    def _length(self, el, name, default):
        value = el.get_length(name)
        if value is None or value is AUTO:
            return int(default)
        if isinstance(value, Percent):
            return int(default)
        return int(value)

    def _thickness(self, el, name):
        raw = el.get(name)
        if raw is None:
            return Thickness()
        try:
            return parse_thickness(raw)
        except ValueError as exc:
            raise DslError(f"{name}: {exc}", element=el) from exc

    def _attached(self, el, name, default):
        value = el.get_length(name)
        if value is None or value is AUTO:
            return default
        if isinstance(value, Percent):
            return default
        return int(value)


def _int(value, default=0):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _float_or_none(value):
    if value is None:
        return None
    try:
        text = str(value).strip().lower()
        if text.endswith("pt"):
            return float(text[:-2])
        if text.endswith("px"):
            return float(text[:-2]) * 0.75
        return float(text)
    except ValueError:
        return None
