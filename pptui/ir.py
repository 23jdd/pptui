from __future__ import annotations


def to_dict(deck):
    return {
        "page": {"width": deck.width, "height": deck.height},
        "theme": {
            "colors": deck.theme.colors,
            "major": [deck.theme.major_latin, deck.theme.major_ea],
            "minor": [deck.theme.minor_latin, deck.theme.minor_ea],
        },
        "slides": [_node(slide) for slide in deck.slides],
    }


def _node(el):
    data = {
        "tag": el.tag,
        "rect": el.rect.to_list(),
        "measured": [el.measured.w, el.measured.h],
    }
    name = el.get("Name")
    if name:
        data["name"] = name
    if el.runs:
        data["text"] = "".join(run.text for run in el.runs)
    if el.children:
        data["children"] = [_node(child) for child in el.children]
    return data
