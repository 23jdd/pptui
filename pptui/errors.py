from __future__ import annotations


class PptuiError(Exception):
    pass


class DslError(PptuiError):
    def __init__(self, message, element=None, line=None, source=None):
        self.message = message
        self.element = element
        self.line = line if line is not None else getattr(element, "line", None)
        self.source = source
        super().__init__(self.describe())

    def describe(self):
        where = []
        if self.source:
            where.append(str(self.source))
        if self.line:
            where.append(str(self.line))
        prefix = ":".join(where)
        target = ""
        tag = getattr(self.element, "tag", None) if self.element is not None else None
        if tag and f"<{tag}>" not in self.message:
            target = f" <{tag}>"
        if prefix:
            return f"{prefix}: {self.message}{target}"
        return f"{self.message}{target}"
