from __future__ import annotations

import io
import zipfile

from lxml import etree
from pptx import Presentation


def verify(data):
    issues = []
    buffer = io.BytesIO(data)
    try:
        archive = zipfile.ZipFile(buffer)
    except zipfile.BadZipFile as exc:
        return [f"not a zip package: {exc}"]

    with archive:
        names = set(archive.namelist())
        if "[Content_Types].xml" not in names:
            issues.append("missing [Content_Types].xml")
        slides = sorted(name for name in names if name.startswith("ppt/slides/slide") and name.endswith(".xml"))
        if not slides:
            issues.append("package contains no slides")
        for name in slides:
            try:
                etree.fromstring(archive.read(name))
            except etree.XMLSyntaxError as exc:
                issues.append(f"{name}: invalid XML: {exc}")
        for name in names:
            if name.startswith("ppt/media/") and archive.getinfo(name).file_size == 0:
                issues.append(f"{name}: empty media part")

    buffer.seek(0)
    try:
        prs = Presentation(buffer)
    except Exception as exc:
        issues.append(f"python-pptx cannot reopen the deck: {exc}")
        return issues

    count = len(prs.slides._sldIdLst)
    if slides and count != len(slides):
        issues.append(f"slide count mismatch: presentation lists {count}, package has {len(slides)}")

    return issues
