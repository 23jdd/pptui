from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path

from lxml import etree


def main():
    source = Path(sys.argv[1])
    outdir = Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    root = etree.parse(str(source)).getroot()
    count = len([element for element in root if etree.QName(element).localname == "Slide"])
    for index in range(1, count + 1):
        copy = deepcopy(root)
        slides = [element for element in copy if etree.QName(element).localname == "Slide"]
        keep = slides[index - 1]
        for element in slides:
            if element is not keep:
                copy.remove(element)
        target = outdir / f"slide-{index:02d}.xml"
        etree.ElementTree(copy).write(str(target), encoding="utf-8", xml_declaration=True, pretty_print=True)
        print(target)


if __name__ == "__main__":
    main()
