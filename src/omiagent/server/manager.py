"""TaskManager — owns tasks, runtimes, the router, and the event fan-out."""

from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .. import events as E
from ..agent.checkpoint import rewind as git_rewind
from ..agent.loop import AgentLoop, LoopConfig
from ..config import Settings, get_settings
from ..gateway.audit import UsageLog
from ..gateway.router import MaxRouter
from ..runtime import create_runtime
from ..store import TaskStore
from ..utils.ids import new_id

_IGNORE_DIRS = {
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
}


class _Busy(Exception):
    pass


@dataclass
class TaskHandle:
    id: str
    meta: dict[str, Any]
    runtime: Any = None
    loop: AgentLoop | None = None
    task: asyncio.Task | None = None
    approved: asyncio.Event = field(default_factory=asyncio.Event)
    queues: set[asyncio.Queue] = field(default_factory=set)
    status: str = "queued"

    @property
    def workspace(self) -> Path:
        return Path(self.meta["workspace"])


class TaskManager:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.store = TaskStore(self.settings.data_dir / "tasks")
        self.usage = UsageLog(self.settings.data_dir / "usage.db")
        self.router = MaxRouter(self.settings.providers, usage=self.usage)
        self._handles: dict[str, TaskHandle] = {}

    # ------------------------------------------------------------ lifecycle
    async def create(self, prompt: str, repo_path: str | None = None, mode: str = "plan") -> str:
        prompt = (prompt or "").strip()
        if not prompt:
            raise ValueError("prompt is required")
        if mode not in ("plan", "auto"):
            raise ValueError("mode must be 'plan' or 'auto'")
        task_id = new_id()
        ws = self.settings.workspaces_dir / task_id / "repo"
        src: Path | None = None
        if repo_path:
            src = Path(repo_path).expanduser().resolve()
            if not src.is_dir():
                raise ValueError(f"repo_path not found: {src}")
        ws.parent.mkdir(parents=True, exist_ok=True)
        if src:
            shutil.copytree(
                src, ws, ignore=shutil.ignore_patterns(*_IGNORE_DIRS), dirs_exist_ok=True
            )
        else:
            ws.mkdir(parents=True, exist_ok=True)

        runtime = await create_runtime(
            self.settings.sandbox, ws, image=self.settings.sandbox_image, sandbox_id=task_id
        )
        meta = {
            "id": task_id,
            "prompt": prompt[:400],
            "mode": mode,
            "runtime": runtime.kind,
            "status": "running",
            "workspace": str(ws),
            "repo": str(src) if src else None,
        }
        self.store.create(task_id, meta)
        h = TaskHandle(id=task_id, meta=meta, runtime=runtime, status="running")
        self._handles[task_id] = h
        h.task = asyncio.create_task(self._run(h, prompt, mode), name=f"omirun-{task_id}")
        return task_id

    async def _run(self, h: TaskHandle, prompt: str, mode: str) -> None:
        async def emit(ev: E.Event) -> None:
            self.store.append(h.id, ev)
            for q in list(h.queues):
                try:
                    q.put_nowait(ev.to_dict())
                except asyncio.QueueFull:
                    pass

        cfg = LoopConfig(
            max_steps=self.settings.max_steps,
            step_timeout_s=self.settings.step_timeout_s,
            budget_usd=self.settings.task_budget_usd,
            plan_approval_timeout_s=self.settings.plan_approval_timeout_s,
        )
        h.loop = AgentLoop(
            router=self.router,
            runtime=h.runtime,
            emit=emit,
            task_id=h.id,
            cfg=cfg,
            approved=h.approved,
            usage_totals=self.usage.totals_for,
        )
        status, summary = "finished", ""
        try:
            res = await h.loop.run(prompt, mode=mode)
            status, summary = res.status, res.summary
        except asyncio.CancelledError:
            status, summary = "cancelled", "cancelled by user"
            await emit(E.status("task cancelled"))
        except Exception as e:  # noqa: BLE001 — a crash must end the task, not the server
            status, summary = "error", f"{type(e).__name__}: {e}"
            await emit(E.error(summary))
            try:
                await emit(E.task_finished(status, summary, 0, 0.0))
            except Exception:  # noqa: BLE001
                pass
        finally:
            h.status = status
            self.store.update_meta(
                h.id,
                status=status,
                summary=summary[:500],
                finished=round(__import__("time").time(), 2),
            )
            for q in list(h.queues):
                try:
                    q.put_nowait({"kind": "__closed__", "payload": {}, "ts": 0})
                except asyncio.QueueFull:
                    pass
            if self.settings.sandbox != "local":
                try:
                    await h.runtime.close()
                except Exception:  # noqa: BLE001
                    pass
            h.loop = None

    # ------------------------------------------------------------- controls
    def get(self, task_id: str) -> TaskHandle | None:
        return self._handles.get(task_id)

    def approve_plan(self, task_id: str) -> bool:
        h = self._handles.get(task_id)
        if not h:
            return False
        h.approved.set()
        return True

    def cancel(self, task_id: str) -> bool:
        h = self._handles.get(task_id)
        if not h or h.task is None or h.task.done():
            return False
        h.task.cancel()
        return True

    async def rewind(self, task_id: str, ref: str) -> bool:
        h = self._handles.get(task_id)
        if h and h.runtime is not None and h.status == "running":
            return await git_rewind(h.runtime, ref)
        if not h:  # archived task: git on the host dir (workspace exists locally either way)
            meta = self.store.load_meta(task_id)
            if not meta:
                return False
            ws = Path(meta["workspace"])
            if not ws.is_dir():
                return False
            import re
            import subprocess

            if not re.match(r"^[0-9a-f]{4,40}$", ref or ""):
                return False
            r = subprocess.run(
                ["git", "reset", "--hard", ref], cwd=ws, capture_output=True, text=True, timeout=30
            )
            return r.returncode == 0
        return False

    # ------------------------------------------------------------------ bus
    def subscribe(self, task_id: str) -> asyncio.Queue:
        h = self._handles.get(task_id)
        q: asyncio.Queue = asyncio.Queue(maxsize=512)
        if h:
            h.queues.add(q)
        return q

    def unsubscribe(self, task_id: str, q: asyncio.Queue) -> None:
        h = self._handles.get(task_id)
        if h:
            h.queues.discard(q)

    # ------------------------------------------------------------- listings
    def list_tasks(self) -> list[dict[str, Any]]:
        return self.store.list()

    def task_detail(self, task_id: str, tail: int = 300) -> dict[str, Any] | None:
        meta = self.store.load_meta(task_id)
        if meta is None:
            return None
        evs = self.store.read_events(task_id)[-tail:]
        meta["events"] = [e.to_dict() for e in evs]
        meta["live"] = task_id in self._handles and self._handles[task_id].status == "running"
        meta["usage"] = self.usage.totals_for(task_id)
        return meta

    def list_files(self, task_id: str) -> list[dict[str, Any]]:
        meta = self.store.load_meta(task_id)
        if not meta:
            return []
        ws = Path(meta["workspace"])
        out = []
        if not ws.is_dir():
            return out
        for root, _dirs, files in os_walk_pruned(ws):
            for fn in files:
                p = Path(root) / fn
                try:
                    out.append({"path": str(p.relative_to(ws)), "size": p.stat().st_size})
                except OSError:
                    pass
                if len(out) >= 800:
                    return out
        return out

    def shutdown(self) -> None:
        for h in self._handles.values():
            if h.task and not h.task.done():
                h.task.cancel()


def os_walk_pruned(ws: Path):
    import os

    for root, dirs, files in os.walk(ws):
        dirs[:] = [d for d in dirs if d not in _IGNORE_DIRS and d != ".git"]
        yield root, dirs, files
