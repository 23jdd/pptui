from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pptx import Presentation
from pptx.util import Emu

from pptui.model import Theme
from pptui.render.theme import apply_theme


def main():
    prs = Presentation()
    prs.slide_width = Emu(12192000)
    prs.slide_height = Emu(6858000)
    apply_theme(prs, Theme())
    target = ROOT / "pptui" / "templates" / "base.pptx"
    target.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(target))
    print(target)


if __name__ == "__main__":
    main()
