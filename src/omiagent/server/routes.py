"""Task REST + WebSocket event stream."""

from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["tasks"])


class CreateTask(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    repo_path: str | None = None
    mode: Literal["plan", "auto"] = "plan"


class RewindReq(BaseModel):
    ref: str = Field(pattern=r"^[0-9a-f]{4,40}$")


def _mgr(request: Request):
    return request.app.state.manager


@router.post("/tasks", status_code=201)
async def create_task(body: CreateTask, request: Request) -> dict:
    try:
        task_id = await _mgr(request).create(body.prompt, body.repo_path, body.mode)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"task_id": task_id}


@router.get("/tasks")
async def list_tasks(request: Request) -> list[dict]:
    return _mgr(request).list_tasks()


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, request: Request, events_tail: int = 300) -> dict:
    detail = _mgr(request).task_detail(task_id, tail=max(1, min(2000, events_tail)))
    if detail is None:
        raise HTTPException(404, "task not found")
    return detail


@router.get("/tasks/{task_id}/events")
async def get_events(task_id: str, request: Request) -> list[dict]:
    mgr = _mgr(request)
    if mgr.store.load_meta(task_id) is None:
        raise HTTPException(404, "task not found")
    return [e.to_dict() for e in mgr.store.read_events(task_id)]


@router.get("/tasks/{task_id}/files")
async def get_files(task_id: str, request: Request) -> list[dict]:
    return _mgr(request).list_files(task_id)


@router.post("/tasks/{task_id}/approve-plan")
async def approve_plan(task_id: str, request: Request) -> dict:
    if not _mgr(request).approve_plan(task_id):
        raise HTTPException(404, "task not found or already finished")
    return {"ok": True}


@router.post("/tasks/{task_id}/cancel")
async def cancel(task_id: str, request: Request) -> dict:
    if not _mgr(request).cancel(task_id):
        raise HTTPException(409, "task not running")
    return {"ok": True}


@router.post("/tasks/{task_id}/rewind")
async def rewind(task_id: str, body: RewindReq, request: Request) -> dict:
    if not await _mgr(request).rewind(task_id, body.ref):
        raise HTTPException(400, "rewind failed (unknown task/ref or sandbox closed)")
    return {"ok": True}


@router.get("/config")
async def config_view(request: Request) -> dict:
    s = _mgr(request).settings
    prov = s.providers
    return {
        "version": __import__("omiagent").__version__,
        "sandbox": s.sandbox,
        "task_budget_usd": s.task_budget_usd,
        "max_steps": s.max_steps,
        "providers_available": [p.name for p in prov.available()],
        "groups": dict(prov.groups),
    }


@router.get("/usage")
async def usage(request: Request) -> dict:
    return _mgr(request).usage.totals()


# ---------------------------------------------------------------- websocket
@router.websocket("/ws/tasks/{task_id}")
async def task_ws(ws: WebSocket, task_id: str) -> None:
    mgr = ws.app.state.manager
    if mgr.store.load_meta(task_id) is None:
        await ws.close(code=4404)
        return
    await ws.accept()
    # backlog first so late/refreshing clients catch up
    for ev in mgr.store.read_events(task_id):
        await ws.send_json(ev.to_dict())
    q = mgr.subscribe(task_id)

    async def forward() -> None:
        while True:
            item = await q.get()
            if isinstance(item, dict) and item.get("kind") == "__closed__":
                break
            await ws.send_json(item)

    async def inbound() -> None:
        while True:
            msg = await ws.receive_json()
            act = (msg or {}).get("action")
            if act == "approve":
                mgr.approve_plan(task_id)
            elif act == "cancel":
                mgr.cancel(task_id)

    fwd, inb = asyncio.create_task(forward()), asyncio.create_task(inbound())
    try:
        done, pending = await asyncio.wait({fwd, inb}, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        mgr.unsubscribe(task_id, q)
        for t in (fwd, inb):
            if not t.done():
                t.cancel()
