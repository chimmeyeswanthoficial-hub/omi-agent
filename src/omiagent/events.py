"""Typed event model — everything the UI shows is one of these."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

KINDS = (
    "task_started",
    "plan_proposed",
    "plan_approved",
    "step_started",
    "reasoning",
    "tool_call",
    "tool_result",
    "verify",
    "checkpoint",
    "cost",
    "error",
    "status",
    "task_finished",
)


@dataclass(slots=True)
class Event:
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "payload": self.payload, "ts": self.ts}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Event:
        return cls(
            kind=d.get("kind", "status"), payload=d.get("payload", {}) or {}, ts=d.get("ts", 0.0)
        )


# -- factories ---------------------------------------------------------------


def task_started(prompt: str, mode: str, runtime: str) -> Event:
    return Event("task_started", {"prompt": prompt, "mode": mode, "runtime": runtime})


def plan_proposed(steps: list[str]) -> Event:
    return Event("plan_proposed", {"steps": steps})


def plan_approved(source: str = "user") -> Event:
    return Event("plan_approved", {"source": source})


def step_started(index: int) -> Event:
    return Event("step_started", {"step": index})


def reasoning(text: str, step: int | None = None) -> Event:
    return Event("reasoning", {"text": text, "step": step})


def tool_call(tool: str, args: dict[str, Any], step: int) -> Event:
    return Event("tool_call", {"tool": tool, "args": args, "step": step})


def tool_result(tool: str, ok: bool, text: str, step: int, elapsed_ms: int = 0) -> Event:
    return Event(
        "tool_result",
        {"tool": tool, "ok": ok, "text": text, "step": step, "elapsed_ms": elapsed_ms},
    )


def verify(ok: bool, text: str, step: int) -> Event:
    return Event("verify", {"ok": ok, "text": text, "step": step})


def checkpoint(commit: str, message: str, step: int) -> Event:
    return Event("checkpoint", {"commit": commit, "message": message, "step": step})


def cost(
    group: str, provider: str, model: str, tokens_in: int, tokens_out: int, usd: float
) -> Event:
    return Event(
        "cost",
        {
            "group": group,
            "provider": provider,
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "usd": usd,
        },
    )


def error(message: str, step: int | None = None) -> Event:
    return Event("error", {"message": message, "step": step})


def status(message: str) -> Event:
    return Event("status", {"message": message})


def task_finished(status_: str, summary: str, steps: int, usd: float) -> Event:
    return Event(
        "task_finished", {"status": status_, "summary": summary, "steps": steps, "usd": usd}
    )
