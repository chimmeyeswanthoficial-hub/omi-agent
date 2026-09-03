"""AgentLoop — the plan → reason → act → verify → self-correct engine."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from .. import events as E
from ..gateway.router import GatewayError, MaxRouter
from ..runtime.base import Runtime
from ..safety.redact import redact_text
from ..tools import REGISTRY, catalog, execute
from . import checkpoint as ckpt
from .context import build_repo_map, detect_verify
from .parser import parse_action
from .prompts import PLANNER, REPLAN_NOTE, SYSTEM

Emit = Callable[[E.Event], Awaitable[None]]

_TRANSCRIPT_TAIL = 24  # messages kept from the tail
_ARG_ECHO_CHARS = 220


@dataclass(slots=True)
class LoopConfig:
    max_steps: int = 80
    step_timeout_s: int = 120
    budget_usd: float = 1.00
    verify_cmd: str | None = None
    plan_approval_timeout_s: int = 25  # auto-continue so headless runs never hang
    temperature_agent: float = 0.15
    temperature_plan: float = 0.3


@dataclass(slots=True)
class LoopResult:
    status: str = "finished"  # finished | max-steps | budget | error
    summary: str = ""
    steps: int = 0
    usd: float = 0.0
    needs_human: bool = False


class AgentLoop:
    def __init__(
        self,
        *,
        router: MaxRouter,
        runtime: Runtime,
        emit: Emit,
        task_id: str = "",
        cfg: LoopConfig | None = None,
        approved: asyncio.Event | None = None,
        usage_totals: Callable[[str], dict[str, float]] | None = None,
    ) -> None:
        self.router = router
        self.rt = runtime
        self.emit = emit
        self.task_id = task_id
        self.cfg = cfg or LoopConfig()
        self.approved = approved
        self.usage_totals = usage_totals

    # ------------------------------------------------------------------ run
    async def run(self, prompt: str, mode: str = "plan") -> LoopResult:
        result = LoopResult()
        await self.emit(E.task_started(redact_text(prompt)[:2000], mode, self.rt.kind))
        await ckpt.ensure_git(self.rt)
        verify_cmd = (
            self.cfg.verify_cmd if self.cfg.verify_cmd is not None else await detect_verify(self.rt)
        )

        plan_text = ""
        if mode == "plan":
            plan_text = await self._make_plan(prompt)
            await self._await_approval()

        repo_map = await build_repo_map(self.rt)
        transcript: list[dict[str, Any]] = []
        consec_failures = 0

        for step in range(1, self.cfg.max_steps + 1):
            result.steps = step
            over_budget = await self._over_budget()
            if over_budget:
                await self.emit(
                    E.error(f"per-task budget ${self.cfg.budget_usd:.2f} reached — stopping")
                )
                result.status, result.summary = "budget", "stopped: task budget exhausted"
                await self.emit(E.task_finished(result.status, result.summary, step, result.usd))
                return result

            await self.emit(E.step_started(step))
            messages = self._messages(prompt, plan_text, repo_map, transcript)
            hint = "plan-reason" if plan_text and step == 1 else None
            try:
                resp = await self.router.chat(
                    messages, task_hint=hint, caller="agent", task_id=self.task_id
                )
            except GatewayError as e:
                await self.emit(E.error(str(e)))
                result.status, result.summary = "error", f"gateway failure: {e}"
                await self.emit(E.task_finished(result.status, result.summary, step, result.usd))
                return result

            result.usd += resp.usd
            await self.emit(
                E.cost(
                    resp.group, resp.provider, resp.model, resp.tokens_in, resp.tokens_out, resp.usd
                )
            )
            action = parse_action(resp.text)
            await self.emit(E.reasoning(action.thought or "(no thought)", step))

            # -- finish / chat-answer path --------------------------------
            if action.tool == "finish":
                summary = str(action.args.get("summary", "")).strip() or resp.text[:800]
                h = await ckpt.snapshot(self.rt, f"final: {summary[:60]}")
                if h:
                    await self.emit(E.checkpoint(h, "final state", step))
                result.status, result.summary = "finished", summary
                result.needs_human = bool(action.args.get("needs_human"))
                await self.emit(
                    E.task_finished(result.status, redact_text(summary), step, result.usd)
                )
                return result

            # -- tool dispatch ----------------------------------------------
            await self.emit(E.tool_call(action.tool, self._small(action.args), step))
            if action.tool not in REGISTRY:
                text = f"unknown tool {action.tool!r}; available: {', '.join(sorted(REGISTRY))}"
                await self.emit(E.tool_result(action.tool, False, text, step))
                transcript.append({"role": "assistant", "content": redact_text(resp.text)[:1500]})
                transcript.append(
                    {"role": "user", "content": f"[tool {action.tool} → error]\n{text}"}
                )
                continue

            res = await execute(action.tool, action.args, self.rt)
            await self.emit(
                E.tool_result(
                    action.tool, res.ok, redact_text(res.text)[:4000], step, res.elapsed_ms
                )
            )
            transcript.append({"role": "assistant", "content": redact_text(resp.text)[:1500]})
            transcript.append(
                {
                    "role": "user",
                    "content": f"[tool {action.tool} → {'ok' if res.ok else 'error'}]\n{redact_text(res.text)[:1800]}",
                }
            )

            # -- checkpoint + verify after mutations --------------------------
            mutated = bool(res.meta.get("mutated")) and res.ok
            if mutated:
                h = await ckpt.snapshot(self.rt, f"step {step}: {action.tool}")
                if h:
                    await self.emit(E.checkpoint(h, f"{action.tool} checkpoint", step))
                if verify_cmd:
                    v = await self.rt.exec(verify_cmd, timeout=min(self.cfg.step_timeout_s, 300))
                    vtext = redact_text((v.stdout + "\n" + v.stderr).strip())
                    await self.emit(E.verify(v.ok, vtext[-2500:], step))
                    transcript.append(
                        {
                            "role": "user",
                            "content": f"[verify `{'`'}{verify_cmd}{'`'} → {'PASSED' if v.ok else 'FAILED'}]\n"
                            + ("ok" if v.ok else vtext[-2200:]),
                        }
                    )
                    consec_failures = 0 if v.ok else consec_failures + 1
                    if consec_failures >= 2:
                        transcript.append({"role": "user", "content": REPLAN_NOTE})
                        await self.emit(E.status("verify failed 2× — injected re-plan directive"))
                        consec_failures = 0

            transcript = transcript[-_TRANSCRIPT_TAIL:]

        result.status = "max-steps"
        result.summary = f"stopped after {self.cfg.max_steps} steps without finish"
        await self.emit(E.error(result.summary))
        await self.emit(E.task_finished(result.status, result.summary, result.steps, result.usd))
        return result

    # ------------------------------------------------------------- helpers
    async def _make_plan(self, prompt: str) -> str:
        try:
            resp = await self.router.chat(
                [
                    {"role": "system", "content": PLANNER},
                    {"role": "user", "content": redact_text(prompt)[:6000]},
                ],
                task_hint="plan-reason",
                temperature=self.cfg.temperature_plan,
                caller="planner",
                task_id=self.task_id,
            )
        except GatewayError as e:
            await self.emit(E.error(f"planner unavailable, proceeding without plan: {e}"))
            return ""
        # prefer a clean {"plan": [...]} object; fall back to action parsing
        steps: list[str] = []
        try:
            obj = json.loads(
                resp.text.strip()
                .removeprefix("```json")
                .removeprefix("```")
                .removesuffix("```")
                .strip()
            )
            if isinstance(obj, dict) and isinstance(obj.get("plan"), list):
                steps = [str(s) for s in obj["plan"] if str(s).strip()][:10]
        except (json.JSONDecodeError, ValueError):
            pass
        if not steps:
            action = parse_action(resp.text)
            if action.args.get("plan"):
                steps = [str(s) for s in action.args["plan"]][:10]
        if not steps:  # last resort: one-step plan from the raw text
            steps = (
                [resp.text.strip()[:300]] if resp.text.strip() else ["execute the task directly"]
            )

        await self.emit(E.plan_proposed(steps))
        return "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps))

    async def _await_approval(self) -> None:
        if self.approved is None:
            await self.emit(E.plan_approved("auto (no UI attached)"))
            return
        try:
            await asyncio.wait_for(self.approved.wait(), timeout=self.cfg.plan_approval_timeout_s)
            await self.emit(E.plan_approved("user"))
        except TimeoutError:
            await self.emit(E.plan_approved("auto (approval window timed out)"))

    async def _over_budget(self) -> bool:
        if self.usage_totals is None or not self.task_id:
            return False
        totals = self.usage_totals(self.task_id)
        return float(totals.get("usd", 0.0)) > self.cfg.budget_usd

    def _messages(
        self, prompt: str, plan: str, repo_map: str, transcript: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        sys = (
            SYSTEM.replace("__CATALOG__", json.dumps(catalog(), indent=1))
            + f"\n## Budget\nThis task stops at ${self.cfg.budget_usd:.2f} provider spend or "
            + f"{self.cfg.max_steps} steps.\n"
        )
        first = f"## Task\n{prompt[:8000]}\n"
        if plan:
            first += f"\n## Approved plan\n{plan[:3000]}\nFollow it; deviate only when evidence says so.\n"
        if repo_map:
            first += f"\n{repo_map[:4000]}\n"
        return [{"role": "system", "content": sys}, {"role": "user", "content": first}, *transcript]

    @staticmethod
    def _small(args: dict[str, Any]) -> dict[str, Any]:
        return {
            k: (v[:_ARG_ECHO_CHARS] + "…" if isinstance(v, str) and len(v) > _ARG_ECHO_CHARS else v)
            for k, v in args.items()
        }
