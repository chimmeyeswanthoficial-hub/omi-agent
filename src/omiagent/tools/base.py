"""Tool base + unified-diff helpers shared by edit/patch/write."""

from __future__ import annotations

import difflib
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..runtime.base import Runtime

MAX_RESULT_CHARS = 6000


@dataclass(slots=True)
class ToolResult:
    ok: bool
    text: str
    elapsed_ms: int = 0
    meta: dict[str, Any] = field(default_factory=dict)


def truncate(s: str, n: int = MAX_RESULT_CHARS) -> str:
    if len(s) <= n:
        return s
    return s[: n // 2] + f"\n…[truncated {len(s) - n} chars]…\n" + s[-n // 2 :]


def unified(old: str, new: str, name: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            old.splitlines(),
            new.splitlines(),
            fromfile=f"a/{name}",
            tofile=f"b/{name}",
            lineterm="",
        )
    )


# ------------------------- minimal unified-diff applier ----------------------

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


@dataclass(slots=True)
class _Hunk:
    old_start: int
    olds: list[str]
    news: list[str]


def parse_patch(text: str) -> dict[str, list[_Hunk]]:
    """{path: [hunks]} from a `--- a/p` / `+++ b/p` style unified diff."""
    files: dict[str, list[_Hunk]] = {}
    cur_path: str | None = None
    hunk: _Hunk | None = None
    for line in text.splitlines():
        if line.startswith(("--- ", "=== ")):
            continue
        if line.startswith("+++ "):
            p = line[4:].strip()
            if p.startswith("b/"):
                p = p[2:]
            cur_path = p
            files.setdefault(cur_path, [])
            hunk = None
            continue
        m = _HUNK_RE.match(line)
        if m and cur_path is not None:
            hunk = _Hunk(int(m.group(1)), [], [])
            files[cur_path].append(hunk)
            continue
        if hunk is not None:
            if line.startswith("+"):
                hunk.news.append(line[1:])
            elif line.startswith("-"):
                hunk.olds.append(line[1:])
            elif line.startswith(" "):
                hunk.olds.append(line[1:])
                hunk.news.append(line[1:])
            elif line == "":
                hunk.olds.append("")
                hunk.news.append("")
    return {p: h for p, h in files.items() if h}


def apply_hunks(old_text: str, hunks: list[_Hunk]) -> str:
    lines = old_text.split("\n") if old_text else []
    offset = 0
    for h in hunks:
        start = max(0, h.old_start - 1 + offset)
        pos = _find(lines, h.olds, start)
        if pos is None and h.olds:
            raise ValueError(f"hunk at line {h.old_start} does not match file context")
        pos = pos if pos is not None else min(start, len(lines))
        lines[pos : pos + len(h.olds)] = h.news
        offset += len(h.news) - len(h.olds)
    return "\n".join(lines)


def _find(lines: list[str], olds: list[str], start: int) -> int | None:
    if not olds:
        return start
    window = range(max(0, start - 25), min(len(lines), start + 250))
    for c in window:
        if lines[c : c + len(olds)] == olds:
            return c
    return None


class Tool(ABC):
    spec: dict[str, Any]

    @abstractmethod
    async def run(self, rt: Runtime, args: dict[str, Any]) -> ToolResult: ...
