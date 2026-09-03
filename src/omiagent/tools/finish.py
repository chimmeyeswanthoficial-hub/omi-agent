from __future__ import annotations

from typing import Any

from ..runtime.base import Runtime
from .base import Tool, ToolResult


class FinishTool(Tool):
    """Terminal signal for the agent loop. `run` is never executed —
    the loop intercepts `finish` before dispatch — but the spec must exist
    so the model can see and call it."""

    spec = {
        "name": "finish",
        "description": "End the task. Call when the request is satisfied or you need a human decision.",
        "args": {
            "summary": "string — what was done / what you need",
            "changed_files": "list[str], optional",
            "needs_human": "bool, optional — true if blocked on a decision",
        },
    }

    async def run(self, rt: Runtime, args: dict[str, Any]) -> ToolResult:  # pragma: no cover
        return ToolResult(ok=False, text="finish is handled by the loop, not the tool dispatcher")
