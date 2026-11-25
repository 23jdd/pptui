from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from .errors import DslError
from .ir import to_dict
from .parse import parse_deck
from .pipeline import render_presentation
from .schema import validate_source
from .verify import verify


def build(source, output=None, *, schema=True, template=None, ir=None, check=True):
    deck = parse_deck(source)
    try:
        if template:
            deck.root.props["template"] = str(Path(template).resolve())
        if schema and deck.source and Path(deck.source).exists():
            validate_source(deck.source)
        prs, _engine = render_presentation(deck)
        buffer = BytesIO()
        prs.save(buffer)
        data = buffer.getvalue()
    except DslError as exc:
        if not exc.source and deck.source:
            exc.source = deck.source
            exc.args = (exc.describe(),)
        raise
    if output:
        target = Path(output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    if ir:
        target = Path(ir)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(to_dict(deck), ensure_ascii=False, indent=2), encoding="utf-8")
    if check:
        issues = verify(data)
        if issues:
            raise RuntimeError("generated deck failed verification:\n" + "\n".join(issues))
    return data
