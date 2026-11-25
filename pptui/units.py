from __future__ import annotations

import re
from dataclasses import dataclass
from typing import NamedTuple

EMU_PER_UNIT = {"in": 914400, "cm": 360000, "mm": 36000, "pt": 12700, "px": 9525, "emu": 1}
INF = 1 << 40
_LENGTH = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*(in|cm|mm|pt|px|emu|%)?\s*$", re.I)


class Auto:
    __slots__ = ()

    def __bool__(self):
        return False

    def __repr__(self):
        return "Auto"


AUTO = Auto()


@dataclass(frozen=True)
class Percent:
    value: float


Length = int | Percent | Auto


def parse_length(text, default_unit="pt", allow_percent=True, allow_auto=True):
    if text is None:
        if allow_auto:
            return AUTO
        raise ValueError("length required")
    raw = str(text).strip()
    if not raw:
        if allow_auto:
            return AUTO
        raise ValueError("length required")
    if raw.lower() == "auto":
        if allow_auto:
            return AUTO
        raise ValueError("'auto' is not allowed here")
    match = _LENGTH.match(raw)
    if not match:
        raise ValueError(f"invalid length {text!r}")
    value = float(match.group(1))
    unit = (match.group(2) or default_unit).lower()
    if unit == "%":
        if not allow_percent:
            raise ValueError(f"percent is not allowed here: {text!r}")
        return Percent(value / 100.0)
    return int(round(value * EMU_PER_UNIT[unit]))


def resolve_length(value, base, fallback=0):
    if value is None or value is AUTO:
        return int(fallback)
    if isinstance(value, Percent):
        return int(round(base * value.value))
    return int(value)


class Thickness(NamedTuple):
    left: int = 0
    top: int = 0
    right: int = 0
    bottom: int = 0

    @property
    def horizontal(self):
        return self.left + self.right

    @property
    def vertical(self):
        return self.top + self.bottom


ZERO_THICKNESS = Thickness()


def parse_thickness(text, default_unit="pt"):
    if text is None:
        return ZERO_THICKNESS
    raw = str(text).strip()
    if not raw:
        return ZERO_THICKNESS
    parts = [part for part in re.split(r"[,\s]+", raw) if part]
    values = [parse_length(part, default_unit=default_unit, allow_percent=False, allow_auto=False) for part in parts]
    if len(values) == 1:
        return Thickness(values[0], values[0], values[0], values[0])
    if len(values) == 2:
        return Thickness(values[1], values[0], values[1], values[0])
    if len(values) == 4:
        return Thickness(values[0], values[1], values[2], values[3])
    raise ValueError(f"invalid thickness {text!r}")


class Size(NamedTuple):
    w: int = 0
    h: int = 0

    def grow(self, other):
        return Size(max(self.w, other.w), max(self.h, other.h))


class Rect(NamedTuple):
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0

    @property
    def right(self):
        return self.x + self.w

    @property
    def bottom(self):
        return self.y + self.h

    @property
    def size(self):
        return Size(self.w, self.h)

    def deflate(self, thickness):
        return Rect(
            self.x + thickness.left,
            self.y + thickness.top,
            max(0, self.w - thickness.horizontal),
            max(0, self.h - thickness.vertical),
        )

    def inflate(self, thickness):
        return Rect(
            self.x - thickness.left,
            self.y - thickness.top,
            self.w + thickness.horizontal,
            self.h + thickness.vertical,
        )

    def to_list(self):
        return [self.x, self.y, self.w, self.h]


def emu_to_pt(value):
    return value / 12700.0


def pt_to_emu(value):
    return int(round(float(value) * 12700))
