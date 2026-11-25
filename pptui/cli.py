from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .build import build
from .errors import PptuiError
from .ir import to_dict
from .layout import LayoutEngine
from .parse import parse_deck
from .schema import SCHEMA_PATH, validate_source
from .verify import verify


def main(argv=None):
    parser = argparse.ArgumentParser(prog="pptui", description="Compile XML decks into .pptx files")
    sub = parser.add_subparsers(dest="command")

    build_parser = sub.add_parser("build", help="build a .pptx from an XML deck")
    build_parser.add_argument("source")
    build_parser.add_argument("-o", "--output")
    build_parser.add_argument("--template")
    build_parser.add_argument("--no-schema", action="store_true")
    build_parser.add_argument("--no-check", action="store_true")
    build_parser.add_argument("--ir", help="write the computed layout tree as JSON")

    ir_parser = sub.add_parser("ir", help="print the computed layout tree as JSON")
    ir_parser.add_argument("source")

    validate_parser = sub.add_parser("validate", help="validate an XML deck against the schema")
    validate_parser.add_argument("source")

    sub.add_parser("schema", help="print the path of the XSD")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == "schema":
            print(SCHEMA_PATH)
            return 0
        if args.command == "validate":
            validate_source(args.source)
            print(f"ok {args.source}")
            return 0
        if args.command == "ir":
            deck = parse_deck(args.source)
            LayoutEngine(deck).run()
            print(json.dumps(to_dict(deck), ensure_ascii=False, indent=2))
            return 0
        if args.command == "build":
            output = args.output or str(Path(args.source).with_suffix(".pptx"))
            data = build(
                args.source,
                output,
                schema=not args.no_schema,
                template=args.template,
                ir=args.ir,
                check=not args.no_check,
            )
            print(f"wrote {output} ({len(data)} bytes)")
            return 0
    except PptuiError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    return 1
