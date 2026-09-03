"""OpenAI-compatible surface: GET /v1/models, POST /v1/chat/completions.

Everything a client needs to point at `model: "max"`; omirouter classifies
each request and picks your best/cheapest provider. Non-streaming v0.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from ..gateway.router import GatewayError

router = APIRouter(prefix="/v1", tags=["gateway"])


class ChatReq(BaseModel):
    model: str = "max"
    messages: list[dict[str, Any]] = Field(min_length=1)
    temperature: float | None = None
    task: str | None = None  # optional explicit group hint (same as X-Omi-Task)
    stream: bool = False


def _check_auth(request: Request, authorization: str | None) -> None:
    key = request.app.state.manager.settings.gateway_key
    if not key:
        return  # open on localhost by default
    supplied = (authorization or "").removeprefix("Bearer ").strip()
    if supplied != key:
        raise HTTPException(401, "missing/invalid bearer key for gateway")


@router.get("/models")
async def models(request: Request, authorization: str | None = Header(default=None)) -> dict:
    _check_auth(request, authorization)
    mgr = request.app.state.manager
    ids = ["max"] + [p.name for p in mgr.settings.providers.available()]
    return {
        "object": "list",
        "data": [{"id": m, "object": "model", "owned_by": "omirouter"} for m in ids],
    }


@router.post("/chat/completions")
async def chat_completions(
    body: ChatReq,
    request: Request,
    authorization: str | None = Header(default=None),
    x_omi_task: str | None = Header(default=None),
) -> dict:
    _check_auth(request, authorization)
    if body.stream:
        raise HTTPException(400, "streaming not supported in v0; call again or use the task API")
    mgr = request.app.state.manager
    try:
        res = await mgr.router.chat(
            body.messages,
            task_hint=body.task or x_omi_task,
            temperature=body.temperature if body.temperature is not None else 0.4,
            caller="gateway",
        )
    except GatewayError as e:
        raise HTTPException(502, str(e)) from e
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:20]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "max",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": res.text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": res.tokens_in,
            "completion_tokens": res.tokens_out,
            "total_tokens": res.tokens_in + res.tokens_out,
        },
        "omi": {"provider": res.provider, "model": res.model, "group": res.group, "usd": res.usd},
    }
