from __future__ import annotations

import os

from PIL import ImageFont

FONTS_DIR = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")

FAMILY_FILES = {
    "calibri": ("calibri.ttf", "calibrib.ttf", "calibrii.ttf", "calibriz.ttf"),
    "cambria": ("cambria.ttc", "cambriab.ttf", "cambriai.ttf", "cambriaz.ttf"),
    "arial": ("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf"),
    "times new roman": ("times.ttf", "timesbd.ttf", "timesi.ttf", "timesbi.ttf"),
    "consolas": ("consola.ttf", "consolab.ttf", "consolai.ttf", "consolaz.ttf"),
    "segoe ui": ("segoeui.ttf", "segoeuib.ttf", "segoeuii.ttf", "segoeuiz.ttf"),
    "microsoft yahei": ("msyh.ttc", "msyhbd.ttc", "msyh.ttc", "msyhbd.ttc"),
    "microsoft yahei ui": ("msyh.ttc", "msyhbd.ttc", "msyh.ttc", "msyhbd.ttc"),
    "simhei": ("simhei.ttf", "simhei.ttf", "simhei.ttf", "simhei.ttf"),
    "simsun": ("simsun.ttc", "simsun.ttc", "simsun.ttc", "simsun.ttc"),
    "georgia": ("georgia.ttf", "georgiab.ttf", "georgiai.ttf", "georgiaz.ttf"),
    "verdana": ("verdana.ttf", "verdanab.ttf", "verdanai.ttf", "verdanaz.ttf"),
    "tahoma": ("tahoma.ttf", "tahomabd.ttf", "tahoma.ttf", "tahomabd.ttf"),
}

FALLBACK_FAMILY = "arial"

_CJK_RANGES = (
    (0x2E80, 0x2FFF),
    (0x3000, 0x303F),
    (0x3040, 0x30FF),
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xF900, 0xFAFF),
    (0xFE30, 0xFE4F),
    (0xFF00, 0xFFEF),
    (0x20000, 0x2FA1F),
)


def is_cjk(ch):
    code = ord(ch)
    for low, high in _CJK_RANGES:
        if low <= code <= high:
            return True
    return False


#: Font size used to probe glyph advances. PIL rounds advances to whole pixels,
#: so measuring at 64px and scaling up under-estimates widths by roughly 1%,
#: which is enough to make PowerPoint break a word that we measured as fitting.
#: Probing large keeps the error well below 0.1%.
PROBE_SIZE = 512


class FontMetrics:
    def __init__(self, fonts_dir=None, probe_size=PROBE_SIZE):
        self.fonts_dir = fonts_dir or FONTS_DIR
        self.probe_size = probe_size
        self._fonts = {}

    def font_path(self, family, bold=False, italic=False):
        name = str(family or "").strip().lower()
        files = FAMILY_FILES.get(name)
        if files is None:
            files = FAMILY_FILES.get(FALLBACK_FAMILY)
        index = (1 if bold else 0) + (2 if italic else 0)
        path = os.path.join(self.fonts_dir, files[index])
        if not os.path.exists(path):
            path = os.path.join(self.fonts_dir, files[0])
        if not os.path.exists(path):
            return None
        return path

    def font(self, family, bold=False, italic=False):
        key = (str(family or "").lower(), bool(bold), bool(italic))
        if key in self._fonts:
            return self._fonts[key]
        path = self.font_path(family, bold, italic)
        font = None
        if path:
            try:
                font = ImageFont.truetype(path, self.probe_size)
            except OSError:
                font = None
        self._fonts[key] = font
        return font

    def width_emu(self, text, family, size_pt, bold=False, italic=False, ea=None):
        if not text:
            return 0
        emu = size_pt * 12700.0
        total = 0.0
        buffer = ""
        for ch in text:
            if ea and is_cjk(ch):
                if buffer:
                    total += self._segment(buffer, family, emu, bold, italic)
                    buffer = ""
                total += self._segment(ch, ea, emu, bold, italic)
            else:
                buffer += ch
        if buffer:
            total += self._segment(buffer, family, emu, bold, italic)
        return int(round(total))

    def _segment(self, text, family, emu, bold, italic):
        font = self.font(family, bold, italic)
        if font is None:
            return self._heuristic(text, emu, bold)
        try:
            pixels = font.getlength(text)
        except Exception:
            return self._heuristic(text, emu, bold)
        value = pixels / self.probe_size * emu
        if bold and self.font_path(family, False, italic) == self.font_path(family, True, italic):
            value *= 1.04
        return value

    @staticmethod
    def _heuristic(text, emu, bold):
        total = 0.0
        for ch in text:
            if ch == " ":
                total += 0.28
            elif ch in "il.,;:!|'`":
                total += 0.26
            elif ch in "mwMW@%":
                total += 0.86
            elif is_cjk(ch):
                total += 1.0
            elif ch.isupper():
                total += 0.64
            else:
                total += 0.52
        if bold:
            total *= 1.04
        return total * emu
