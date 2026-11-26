from __future__ import annotations

from pathlib import Path

from lxml import etree

from .errors import DslError

SCHEMA_PATH = Path(__file__).resolve().parent / "schema" / "pptui.xsd"
_cache = {"schema": None}


def load_schema():
    if _cache["schema"] is None:
        if not SCHEMA_PATH.exists():
            raise DslError(f"schema file not found: {SCHEMA_PATH}")
        _cache["schema"] = etree.XMLSchema(etree.parse(str(SCHEMA_PATH)))
    return _cache["schema"]


def validate_source(source):
    schema = load_schema()
    try:
        document = etree.parse(str(source))
    except etree.XMLSyntaxError as exc:
        raise DslError(f"XML parse error: {exc}", source=str(source)) from exc
    if schema.validate(document):
        return True
    messages = []
    for error in schema.error_log:
        messages.append(f"  line {error.line}: {error.message}")
    raise DslError("XML does not match the pptui schema:\n" + "\n".join(messages), source=str(source))


def validate_tree(root):
    schema = load_schema()
    string = etree.tostring(root)
    document = etree.fromstring(string)
    if schema.validate(document):
        return True
    messages = [f"  line {error.line}: {error.message}" for error in schema.error_log]
    raise DslError("XML does not match the pptui schema:\n" + "\n".join(messages))
