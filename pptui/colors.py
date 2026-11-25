from __future__ import annotations

import re
from dataclasses import dataclass

THEME_KEYS = (
    "dk1",
    "lt1",
    "dk2",
    "lt2",
    "accent1",
    "accent2",
    "accent3",
    "accent4",
    "accent5",
    "accent6",
    "hlink",
    "folHlink",
)

ALIASES = {
    "text1": "dk1",
    "background1": "lt1",
    "text2": "dk2",
    "background2": "lt2",
    "hyperl1nk": "hlink",
    "hyperlink": "hlink",
}

_HEX = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


@dataclass(frozen=True)
class Color:
    kind: str
    value: str
    alpha: int | None = None

    @property
    def hex(self):
        return self.value.upper()

    def __str__(self):
        if self.kind == "scheme":
            return f"@{self.value}"
        return f"#{self.value.upper()}"


def parse_color(text, named=None):
    if text is None:
        return None
    raw = str(text).strip()
    if not raw:
        return None
    if raw.lower() in ("none", "transparent"):
        return None
    if raw.startswith("@"):
        key = raw[1:].strip()
        key = ALIASES.get(key.lower(), key)
        if key not in THEME_KEYS:
            raise ValueError(f"unknown theme color {raw!r}")
        return Color("scheme", key)
    if raw.startswith("$"):
        key = raw[1:].strip()
        if not named or key not in named:
            raise ValueError(f"unknown named color {raw!r}")
        value = named[key]
        if isinstance(value, Color):
            return value
        return parse_color(value, named)
    match = _HEX.match(raw)
    if not match:
        raise ValueError(f"invalid color {raw!r}")
    digits = match.group(1)
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    alpha = None
    if len(digits) == 8:
        alpha = int(digits[6:8], 16)
        digits = digits[:6]
    return Color("srgb", digits.upper(), alpha)


def scheme_or_hex(color, theme):
    if color is None:
        return None
    if color.kind == "srgb":
        return color.value
    return theme.colors.get(color.value, "000000")
