from __future__ import annotations

from typing import Any

from ..runtime.base import Runtime
from .base import Tool, ToolResult, truncate

MAX_LINES = 400


class ReadFileTool(Tool):
    spec = {
        "name": "read_file",
        "description": "Read a file from the workspace with line numbers. Returns at most 400 lines.",
        "args": {
            "path": "string — workspace-relative",
            "offset": "int, optional — 1-based start line",
            "limit": "int, optional",
        },
    }

    async def run(self, rt: Runtime, args: dict[str, Any]) -> ToolResult:
        path = str(args.get("path", "")).strip()
        if not path:
            return ToolResult(ok=False, text="read_file: missing `path`")
        try:
            offset = max(1, int(args.get("offset") or 1))
            limit = min(MAX_LINES, max(1, int(args.get("limit") or 200)))
        except (TypeError, ValueError):
            offset, limit = 1, 200
        content = await rt.read_file(path)
        lines = content.split("\n")
        window = lines[offset - 1 : offset - 1 + limit]
        body = "\n".join(f"{offset + i}: {ln}" for i, ln in enumerate(window))
        shown_end = offset + len(window) - 1
        footer = ""
        if shown_end < len(lines):
            footer = f"\n…[{len(lines) - shown_end} more lines; call read_file with offset={shown_end + 1}]"
        return ToolResult(ok=True, text=truncate(body + footer), meta={"total_lines": len(lines)})
