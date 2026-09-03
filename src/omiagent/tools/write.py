from __future__ import annotations

from typing import Any

from ..runtime.base import Runtime
from .base import Tool, ToolResult, unified


class WriteFileTool(Tool):
    spec = {
        "name": "write_file",
        "description": "Create or fully overwrite a file. For small changes prefer edit_file.",
        "args": {"path": "string — workspace-relative", "content": "string — full file content"},
    }

    async def run(self, rt: Runtime, args: dict[str, Any]) -> ToolResult:
        path = str(args.get("path", "")).strip()
        content = args.get("content")
        if not path or not isinstance(content, str):
            return ToolResult(ok=False, text="write_file: needs `path` and string `content`")
        try:
            old = await rt.read_file(path)
            created = False
        except FileNotFoundError:
            old, created = "", True
        await rt.write_file(path, content)
        added = content.count("\n") + (1 if content else 0)
        verb = "created" if created else "wrote"
        diff = "" if created else f"\n{unified(old, content, path)[:3500]}"
        return ToolResult(
            ok=True,
            text=f"{verb} {path} ({added} lines){diff}",
            meta={"path": path, "mutated": True, "created": created},
        )
