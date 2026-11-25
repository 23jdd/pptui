from __future__ import annotations

from .layout import LayoutEngine
from .parse import parse_deck
from .render.slide import render_deck
from .render.theme import apply_theme


def layout_deck(deck):
    return LayoutEngine(deck).run()


def render_presentation(deck):
    engine = LayoutEngine(deck).run()
    prs = render_deck(deck, engine.metrics)
    apply_theme(prs, deck.theme)
    return prs, engine
