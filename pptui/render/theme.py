from __future__ import annotations

from lxml import etree
from pptx.oxml.ns import qn

from ..colors import THEME_KEYS

NSMAP = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}


def apply_theme(prs, theme):
    for part in prs.part.package.iter_parts():
        if str(part.partname).endswith("theme/theme1.xml"):
            _patch_part(part, theme)


def _patch_part(part, theme):
    root = etree.fromstring(part.blob)
    _patch_tree(root, theme)
    data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    try:
        part._blob = data
    except AttributeError:
        element = getattr(part, "_element", None)
        if element is not None:
            part._element = root


def _patch_tree(root, theme):
    scheme = root.find(".//a:clrScheme", NSMAP)
    if scheme is not None:
        for key in THEME_KEYS:
            node = scheme.find("a:" + key, NSMAP)
            if node is None:
                node = etree.SubElement(scheme, qn("a:" + key))
            for child in list(node):
                node.remove(child)
            color = etree.SubElement(node, qn("a:srgbClr"))
            color.set("val", str(theme.colors.get(key, "000000")).upper())
        scheme.set("name", "pptui")

    fonts = root.find(".//a:fontScheme", NSMAP)
    if fonts is None:
        return
    fonts.set("name", "pptui")
    for tag, latin, east_asian in (
        ("majorFont", theme.major_latin, theme.major_ea),
        ("minorFont", theme.minor_latin, theme.minor_ea),
    ):
        node = fonts.find("a:" + tag, NSMAP)
        if node is None:
            node = etree.SubElement(fonts, qn("a:" + tag))
        _set_font(node, "latin", latin)
        _set_font(node, "ea", east_asian)


def _set_font(node, tag, face):
    child = node.find("a:" + tag, NSMAP)
    if child is None:
        child = etree.Element(qn("a:" + tag))
        tail = node.find("a:cs", NSMAP)
        if tail is not None:
            tail.addprevious(child)
        else:
            node.insert(0, child) if tag == "latin" else node.append(child)
    if face:
        child.set("typeface", str(face))
