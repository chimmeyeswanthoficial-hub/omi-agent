"""Parse the model's JSON action. Malformed output degrades to a chat answer
(tool=finish) instead of crashing the loop — same UX as arena.ai/agent for Q&A.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.S)


@dataclass(slots=True)
class Action:
    thought: str
    tool: str
    args: dict[str, Any] = field(default_factory=dict)


def _first_balanced(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth, in_str, esc = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def parse_action(text: str) -> Action:
    candidates = []
    fenced = _FENCE.search(text or "")
    if fenced:
        candidates.append(fenced.group(1))
    balanced = _first_balanced(text or "")
    if balanced:
        candidates.append(balanced)
    for cand in candidates:
        try:
            obj = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        act = obj.get("action") if isinstance(obj.get("action"), dict) else obj
        tool = str(act.get("tool", "")) or str(obj.get("tool", ""))
        args = act.get("args") if isinstance(act.get("args"), dict) else obj.get("args")
        thought = str(obj.get("thought", "")).strip()
        if tool and isinstance(args, dict):
            return Action(thought=thought, tool=tool, args=args)
    # fallback: treat the whole reply as a final answer
    return Action(
        thought=(text or "").strip()[:400],
        tool="finish",
        args={"summary": (text or "").strip() or "(empty reply)"},
    )
