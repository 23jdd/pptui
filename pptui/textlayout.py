from __future__ import annotations

from dataclasses import dataclass

from .metrics import is_cjk
from .model import split_runs
from .units import INF, Size

CLOSING = set("，。、；：？！）】》」』”’,.;:?!)]}>%")
OPENING = set("（【《「『“‘([{<")
SPACES = " \t\u00a0\u3000"


@dataclass
class Token:
    text: str
    run: object
    width: int
    kind: str


def tokens_for(runs, metrics):
    tokens = []
    for run in runs:
        buffer = ""
        for ch in run.text:
            if ch in SPACES:
                if buffer:
                    tokens.append(_token(buffer, run, metrics, "word"))
                    buffer = ""
                tokens.append(_token(ch, run, metrics, "space"))
            elif is_cjk(ch):
                if buffer:
                    tokens.append(_token(buffer, run, metrics, "word"))
                    buffer = ""
                tokens.append(_token(ch, run, metrics, "cjk"))
            else:
                buffer += ch
        if buffer:
            tokens.append(_token(buffer, run, metrics, "word"))
    return tokens


def _token(text, run, metrics, kind):
    width = metrics.width_emu(text, run.family, run.size, run.bold, run.italic, ea=run.ea)
    width += _spacing_emu(run) * len(text)
    return Token(text, run, width, kind)


def _spacing_emu(run):
    return int(round(run.spacing * 12700))


def _split_token(token, max_w, metrics):
    pieces = []
    buffer = ""
    width = 0
    spacing = _spacing_emu(token.run)
    for ch in token.text:
        w = metrics.width_emu(ch, token.run.family, token.run.size, token.run.bold, token.run.italic, ea=token.run.ea)
        w += spacing
        if buffer and width + w > max_w:
            pieces.append(Token(buffer, token.run, width, token.kind))
            buffer = ""
            width = 0
        buffer += ch
        width += w
    if buffer:
        pieces.append(Token(buffer, token.run, width, token.kind))
    return pieces


def wrap_tokens(tokens, max_w, metrics):
    if not tokens:
        return [[]]
    lines = [[]]
    width = 0
    for token in tokens:
        if token.kind == "space" and not lines[-1]:
            continue
        if width + token.width <= max_w or not lines[-1]:
            if token.width > max_w and token.kind == "word" and len(token.text) > 1:
                pieces = _split_token(token, max_w, metrics)
                for piece in pieces:
                    if width + piece.width > max_w and lines[-1]:
                        lines.append([piece])
                        width = piece.width
                    else:
                        lines[-1].append(piece)
                        width += piece.width
                continue
            lines[-1].append(token)
            width += token.width
        elif token.text and token.text[0] in CLOSING:
            lines[-1].append(token)
            width += token.width
        else:
            lines.append([token])
            width = token.width
    return lines


def line_height_emu(line, base_size, line_height_pt=None):
    if line_height_pt:
        return int(round(float(line_height_pt) * 12700))
    size = max((token.run.size for token in line), default=base_size)
    return int(round(size * 1.2 * 12700))


def measure_runs(runs, avail_w, metrics, wrap=True, line_height_pt=None, base_size=18.0, stats=None):
    paragraphs = split_runs(runs)
    total_h = 0
    max_w = 0
    wrapped = False
    for paragraph in paragraphs:
        tokens = tokens_for(paragraph, metrics)
        if wrap and avail_w < INF:
            lines = wrap_tokens(tokens, max(1, avail_w), metrics) if tokens else [[]]
        else:
            lines = [tokens] if tokens else [[]]
        if len(lines) > 1:
            wrapped = True
        for line in lines:
            line_w = sum(token.width for token in line)
            max_w = max(max_w, line_w)
            total_h += line_height_emu(line, base_size, line_height_pt)
    if stats is not None:
        stats["wrapped"] = wrapped
    return Size(max_w, total_h)
