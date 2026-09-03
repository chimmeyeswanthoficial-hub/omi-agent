"""Tool registry — the agent's action vocabulary, runtime-agnostic."""

from __future__ import annotations

import time
from typing import Any

from ..runtime.base import ExecResult, Runtime  # noqa: F401 (re-export for typing)
from .base import Tool, ToolResult
from .bash import BashTool
from .edit import EditFileTool
from .finish import FinishTool
from .patch import ApplyPatchTool
from .read import ReadFileTool
from .search import SearchTool
from .write import WriteFileTool

REGISTRY: dict[str, Tool] = {}


def _register(tool: Tool) -> None:
    REGISTRY[tool.spec["name"]] = tool


for _t in (
    BashTool(),
    ReadFileTool(),
    WriteFileTool(),
    EditFileTool(),
    SearchTool(),
    ApplyPatchTool(),
    FinishTool(),
):
    _register(_t)


def catalog() -> list[dict[str, Any]]:
    """Machine-readable tool list injected into the system prompt."""
    return [t.spec for t in REGISTRY.values()]


async def execute(name: str, args: dict[str, Any], runtime: Runtime) -> ToolResult:
    tool = REGISTRY.get(name)
    if tool is None:
        return ToolResult(
            ok=False, text=f"unknown tool {name!r}; available: {', '.join(sorted(REGISTRY))}"
        )
    t0 = time.monotonic()
    try:
        res = await tool.run(runtime, args or {})
    except FileNotFoundError as e:
        res = ToolResult(ok=False, text=f"file error: {e}")
    except PermissionError as e:
        res = ToolResult(ok=False, text=f"refused: {e}")
    except Exception as e:  # noqa: BLE001 — a tool crash must not kill the loop
        res = ToolResult(ok=False, text=f"tool {name} crashed: {type(e).__name__}: {e}")
    res.elapsed_ms = int((time.monotonic() - t0) * 1000)
    return res


__all__ = ["REGISTRY", "ToolResult", "catalog", "execute"]
