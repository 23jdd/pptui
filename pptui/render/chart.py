from __future__ import annotations

from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.util import Emu, Pt

from ..colors import scheme_or_hex
from ..errors import DslError

CHART_TYPES = {
    "column": XL_CHART_TYPE.COLUMN_CLUSTERED,
    "bar": XL_CHART_TYPE.BAR_CLUSTERED,
    "line": XL_CHART_TYPE.LINE_MARKERS,
    "area": XL_CHART_TYPE.AREA,
    "pie": XL_CHART_TYPE.PIE,
    "doughnut": XL_CHART_TYPE.DOUGHNUT,
}

LEGEND = {
    "bottom": XL_LEGEND_POSITION.BOTTOM,
    "top": XL_LEGEND_POSITION.TOP,
    "left": XL_LEGEND_POSITION.LEFT,
    "right": XL_LEGEND_POSITION.RIGHT,
}


def render_chart(shapes, el, ctx):
    series = el.meta.get("series") or []
    if not series:
        raise DslError("Chart requires at least one <Series>", element=el)
    kind = str(el.get("Type", "Column")).strip().lower()
    chart_type = CHART_TYPES.get(kind)
    if chart_type is None:
        raise DslError(f"unsupported chart type {kind!r}", element=el)

    categories = el.meta.get("categories") or [str(index + 1) for index in range(len(series[0]["values"]))]
    data = CategoryChartData()
    data.categories = categories
    for item in series:
        data.add_series(item["name"], item["values"])

    graphic = shapes.add_chart(
        chart_type,
        Emu(el.rect.x),
        Emu(el.rect.y),
        Emu(el.rect.w),
        Emu(el.rect.h),
        data,
    )
    chart = graphic.chart
    font_size = _font_size(el)

    title = el.get("Title")
    if title:
        chart.has_title = True
        chart.chart_title.text_frame.text = str(title)
        chart.chart_title.text_frame.paragraphs[0].font.size = Pt(16)
        chart.chart_title.text_frame.paragraphs[0].font.bold = True

    legend = str(el.get("Legend", "Bottom")).strip().lower()
    if legend == "none":
        chart.has_legend = False
    else:
        chart.has_legend = True
        chart.legend.position = LEGEND.get(legend, XL_LEGEND_POSITION.BOTTOM)
        chart.legend.include_in_layout = False
        chart.legend.font.size = Pt(font_size)

    chart.font.size = Pt(font_size)

    for index, item in enumerate(series):
        if index >= len(chart.series):
            break
        color = item.get("color")
        if color is None:
            continue
        rgb = RGBColor.from_string(scheme_or_hex(color, ctx.deck.theme))
        target = chart.series[index]
        if kind in ("line",):
            target.format.line.color.rgb = rgb
            target.format.line.width = Pt(2.5)
        else:
            target.format.fill.solid()
            target.format.fill.fore_color.rgb = rgb

    plot = chart.plots[0]
    if kind in ("pie", "doughnut"):
        plot.has_data_labels = True
        labels = plot.data_labels
        labels.show_percentage = True
        labels.show_value = False
        labels.show_category_name = False
        labels.font.size = Pt(font_size)
    elif el.get_bool("DataLabels", False):
        plot.has_data_labels = True
        plot.data_labels.show_value = True
        plot.data_labels.font.size = Pt(font_size)


def _font_size(el):
    raw = el.get("FontSize", "12")
    text = str(raw).strip().lower()
    if text.endswith("pt"):
        text = text[:-2]
    try:
        return float(text)
    except ValueError:
        return 12.0
