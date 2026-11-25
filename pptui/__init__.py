from __future__ import annotations

from .build import build
from .errors import DslError, PptuiError
from .layout import LayoutEngine
from .parse import parse_deck
from .pipeline import layout_deck, render_presentation
from .verify import verify

__version__ = "0.1.0"

__all__ = [
    "DslError",
    "LayoutEngine",
    "PptuiError",
    "build",
    "layout_deck",
    "parse_deck",
    "render_presentation",
    "verify",
    "__version__",
]
