from __future__ import annotations

from lxml import etree
from pptx.oxml.ns import qn

A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


def a(tag):
    return "{%s}%s" % (A_NS, tag)


FILL_TAGS = {a(tag) for tag in ("noFill", "solidFill", "gradFill", "blipFill", "pattFill", "grpFill")}
SPPR_TAIL = {a(tag) for tag in ("ln", "effectLst", "effectDag", "scene3d", "sp3d", "extLst")}
RPR_TAIL = {
    a(tag)
    for tag in (
        "effectLst",
        "highlight",
        "uLnTx",
        "uLn",
        "uFillTx",
        "uFill",
        "latin",
        "ea",
        "cs",
        "sym",
        "hlinkClick",
        "hlinkMouseOver",
        "rtl",
        "extLst",
    )
}
TCPR_TAIL = {a(tag) for tag in ("headers", "extLst")}
BODYPR_TAIL = {a(tag) for tag in ("scene3d", "sp3d", "flatTx", "extLst")}
BGPR_TAIL = {a(tag) for tag in ("effectLst", "extLst")}
EMPTY = frozenset()


def fill_element(color):
    solid = etree.Element(a("solidFill"))
    if color.kind == "scheme":
        child = etree.SubElement(solid, a("schemeClr"))
        child.set("val", color.value)
    else:
        child = etree.SubElement(solid, a("srgbClr"))
        child.set("val", color.value.upper())
    if color.alpha is not None:
        alpha = etree.SubElement(child, a("alpha"))
        alpha.set("val", str(int(round(color.alpha / 255.0 * 100000))))
    return solid


def set_fill(parent, color, tails=EMPTY, none_fill=True):
    if parent is None:
        return
    for child in list(parent):
        if child.tag in FILL_TAGS:
            parent.remove(child)
    if color is None:
        if not none_fill:
            return
        element = etree.Element(a("noFill"))
    else:
        element = fill_element(color)
    for index, child in enumerate(parent):
        if child.tag in tails:
            parent.insert(index, element)
            return
    parent.append(element)


def set_run_color(rPr, color):
    if color is not None:
        set_fill(rPr, color, RPR_TAIL, none_fill=False)


def set_run_fonts(rPr, latin, east_asian):
    for tag, face in (("latin", latin), ("ea", east_asian), ("cs", east_asian)):
        if not face:
            continue
        node = rPr.find(a(tag))
        if node is None:
            node = etree.SubElement(rPr, a(tag))
        node.set("typeface", str(face))


def set_shape_fill(shape, color):
    set_fill(shape._element.spPr, color, SPPR_TAIL)


def drop_style(shape):
    style = shape._element.find(qn("p:style"))
    if style is not None:
        shape._element.remove(style)


def set_shape_line(shape, color, width=None):
    spPr = shape._element.spPr
    ln = spPr.find(a("ln"))
    if ln is None:
        ln = etree.SubElement(spPr, a("ln"))
    set_fill(ln, color, EMPTY, none_fill=True)
    if width is not None:
        ln.set("w", str(int(width)))


def set_border_element(parent, side, color, width):
    ln = etree.Element(a(side))
    ln.set("w", str(int(width)))
    ln.set("cap", "flat")
    ln.set("cmpd", "sng")
    ln.set("algn", "ctr")
    solid = etree.SubElement(ln, a("solidFill"))
    if color.kind == "scheme":
        child = etree.SubElement(solid, a("schemeClr"))
        child.set("val", color.value)
    else:
        child = etree.SubElement(solid, a("srgbClr"))
        child.set("val", color.value.upper())
    return ln


def set_cell_borders(tc, color, width, sides=("lnL", "lnR", "lnT", "lnB")):
    tcPr = tc.get_or_add_tcPr()
    for index, side in enumerate(sides):
        for old in tcPr.findall(a(side)):
            tcPr.remove(old)
        if color is None:
            continue
        tcPr.insert(index, set_border_element(tcPr, side, color, width))


def set_norm_autofit(txBody, scale):
    for tag in ("noAutofit", "normAutofit", "spAutoFit"):
        for node in txBody.findall(a(tag)):
            txBody.remove(node)
    node = etree.SubElement(txBody, a("normAutofit"))
    node.set("fontScale", str(int(round(scale * 100000))))


def set_bullet(pPr, char=None, auto_number=False, marL=0, indent=0):
    pPr.set("marL", str(int(marL)))
    pPr.set("indent", str(int(indent)))
    for tag in ("buNone", "buChar", "buAutoNum", "buFont", "buClr"):
        for node in pPr.findall(a(tag)):
            pPr.remove(node)
    nodes = []
    if auto_number:
        nodes.append(etree.Element(a("buFont")))
        nodes.append(etree.Element(a("buAutoNum")))
        nodes[0].set("typeface", "Arial")
        nodes[1].set("type", "arabicPeriod")
    elif char:
        nodes.append(etree.Element(a("buFont")))
        nodes.append(etree.Element(a("buChar")))
        nodes[0].set("typeface", "Arial")
        nodes[1].set("char", char)
    else:
        nodes.append(etree.Element(a("buNone")))
    tail = {a("tabLst"), a("defRPr"), a("extLst")}
    for node in nodes:
        inserted = False
        for index, child in enumerate(pPr):
            if child.tag in tail:
                pPr.insert(index, node)
                inserted = True
                break
        if not inserted:
            pPr.append(node)


def set_paragraph_spacing(p, before=None, after=None, line=None):
    if before is not None:
        p.space_before = before
    if after is not None:
        p.space_after = after
    if line is not None:
        p.line_spacing = line
