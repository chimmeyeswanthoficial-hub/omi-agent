"""MaxRouter — one virtual model (`max`), task-classified fan-out with
fallback chains and in-memory cooldowns. The heart of omirouter.
"""

from __future__ import annotations

import asyncio
import os
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from ..config import ProviderCfg, ProvidersCfg
from ..safety.redact import redact_text

# complete(dep, messages, temperature) -> ChatResult   (injectable for tests/demos)
CompleteFn = Callable[[ProviderCfg, list[dict[str, Any]], float], Awaitable["ChatResult"]]


@dataclass(slots=True)
class ChatResult:
    text: str
    provider: str = ""
    model: str = ""
    group: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    usd: float = 0.0
    elapsed_ms: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


class GatewayError(RuntimeError):
    """Every healthy deployment in the chain failed."""


_GROUPS = ("code-edit", "plan-reason", "shell-debug", "long-context", "vision")

_RE_CODE = re.compile(r"```", re.S)
_RE_EDIT_INTENT = re.compile(
    r"\b(fix|refactor|implement|edit|change|add|remove|patch|debug|write|modify|rename)\b", re.I
)
_RE_REASON_INTENT = re.compile(
    r"\b(plan|why|architect|design|explain|analyse|analyze|review)\b", re.I
)


def last_user_text(messages: list[dict[str, Any]]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            c = m.get("content", "")
            if isinstance(c, list):  # multimodal parts
                return " ".join(str(p.get("text", "")) for p in c if isinstance(p, dict))
            return str(c)
    return ""


def classify(messages: list[dict[str, Any]], hint: str | None = None) -> str:
    """Map a request to a task group. Deterministic heuristic v0.

    Priority: explicit hint (X-Omi-Task / agent step kind) → heuristics:
    images → vision; huge payload → long-context; planning words → plan-reason;
    code fences or edit intent → code-edit; else shell-debug (cheap+fast).
    """
    if hint and hint in _GROUPS:
        return hint
    for m in messages:
        if isinstance(m.get("content"), list) and any(
            isinstance(p, dict) and p.get("type") == "image_url" for p in m["content"]
        ):
            return "vision"
    text = last_user_text(messages)
    if len(text) > 60_000:
        return "long-context"
    if _RE_REASON_INTENT.search(text) and not _RE_EDIT_INTENT.search(text):
        return "plan-reason"
    fences = len(_RE_CODE.findall(text))
    if fences >= 2 or _RE_EDIT_INTENT.search(text):
        return "code-edit"
    return "shell-debug"


class MaxRouter:
    def __init__(
        self,
        cfg: ProvidersCfg,
        complete: CompleteFn | None = None,
        usage: Any | None = None,  # UsageLog-like: .record(**kw)
    ) -> None:
        self.cfg = cfg
        self._complete = complete or self._litellm_complete
        self.usage = usage
        self._cooldown: dict[str, float] = {}  # provider name -> resume-at ts
        self.failures: dict[str, int] = {}

    # -- provider call (production path) ------------------------------------
    async def _litellm_complete(
        self, dep: ProviderCfg, messages: list[dict[str, Any]], temperature: float
    ) -> ChatResult:
        import litellm

        litellm.drop_params = True
        api_key = os.environ.get(dep.api_key_env or "", "").strip() or None
        t0 = time.monotonic()
        resp = await litellm.acompletion(
            model=dep.model,
            messages=messages,
            temperature=temperature,
            api_key=api_key,
            max_retries=0,
        )
        text = (resp.choices[0].message.content or "") if resp.choices else ""
        u = getattr(resp, "usage", None)
        try:
            from litellm.utils import cost_per_token

            pin, pout = cost_per_token(prompt_tokens=u, completion_tokens=u)
            usd = float(pin) + float(pout)
        except Exception:
            usd = 0.0
        return ChatResult(
            text=text,
            tokens_in=int(getattr(u, "prompt_tokens", 0) or 0),
            tokens_out=int(getattr(u, "completion_tokens", 0) or 0),
            usd=usd,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
            raw={"id": getattr(resp, "id", "")},
        )

    # -- routing --------------------------------------------------------------
    def in_cooldown(self, name: str) -> bool:
        return time.monotonic() < self._cooldown.get(name, 0.0)

    def _cool(self, name: str) -> None:
        self._cooldown[name] = time.monotonic() + self.cfg.router.cooldown_s

    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        task_hint: str | None = None,
        temperature: float = 0.2,
        caller: str = "agent",
        task_id: str | None = None,
    ) -> ChatResult:
        group = classify(messages, task_hint)
        chain = self.cfg.chain(group)
        if not chain:
            raise GatewayError(
                "no providers configured/available — add a key to .env or edit configs/providers.yaml"
            )
        last_err: Exception | None = None
        for dep in chain:
            if self.in_cooldown(dep.name):
                continue
            for attempt in range(self.cfg.router.max_retries + 1):
                try:
                    res = await self._call(dep, messages, temperature)
                    res.provider, res.model, res.group = dep.name, dep.model, group
                    self.failures[dep.name] = 0
                    if self.usage is not None:
                        self.usage.record(
                            task_id=task_id,
                            caller=caller,
                            group=group,
                            provider=dep.name,
                            model=dep.model,
                            tokens_in=res.tokens_in,
                            tokens_out=res.tokens_out,
                            usd=res.usd,
                            elapsed_ms=res.elapsed_ms,
                        )
                    return res
                except Exception as e:  # noqa: BLE001 — chain must walk on ANY failure
                    last_err = e
                    # rate limit / server errors → cool down + move on fast
                    code = getattr(getattr(e, "status_code", None), "value", None) or getattr(
                        e, "status_code", None
                    )
                    if attempt >= 0 and (code in (429, 500, 502, 503) or _looks_transient(str(e))):
                        break
                    await asyncio.sleep(0.2 * (attempt + 1))
            self.failures[dep.name] = self.failures.get(dep.name, 0) + 1
            if self.failures[dep.name] >= 2:
                self._cool(dep.name)
        raise GatewayError(f"all providers failed for group '{group}': {last_err}")

    async def _call(
        self, dep: ProviderCfg, messages: list[dict[str, Any]], temperature: float
    ) -> ChatResult:
        messages = [
            {**m, "content": m["content"]} if not isinstance(m.get("content"), str) else m
            for m in messages
        ]
        # never leak keys into provider logs via transcript echo
        messages = [
            {**m, "content": redact_text(m["content"])} if isinstance(m.get("content"), str) else m
            for m in messages
        ]
        return await self._complete(dep, messages, temperature)


def _looks_transient(msg: str) -> bool:
    return any(
        s in msg.lower()
        for s in ("429", "rate limit", "timeout", "temporarily", "overloaded", "reset")
    )
