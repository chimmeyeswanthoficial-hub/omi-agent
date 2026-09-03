from __future__ import annotations

from typing import Any

from ..runtime.base import Runtime
from ..safety.policy import check_command
from .base import Tool, ToolResult, truncate


class BashTool(Tool):
    spec = {
        "name": "bash",
        "description": "Run a shell command in the sandbox (cwd = repo root). For builds, tests, git, installs.",
        "args": {"cmd": "string — command", "timeout": "int, optional — seconds (default 120)"},
    }

    async def run(self, rt: Runtime, args: dict[str, Any]) -> ToolResult:
        cmd = str(args.get("cmd", "")).strip()
        if not cmd:
            return ToolResult(ok=False, text="bash: empty `cmd`")
        allowed, reason = check_command(cmd)
        if not allowed:
            return ToolResult(ok=False, text=reason)
        try:
            timeout = float(args.get("timeout") or 120)
        except (TypeError, ValueError):
            timeout = 120
        r = await rt.exec(cmd, timeout=min(max(timeout, 1), 600))
        text = r.stdout if r.ok else (r.stdout + ("\n" if r.stdout and r.stderr else "") + r.stderr)
        return ToolResult(
            ok=r.ok,
            text=truncate(f"[exit {r.exit_code}]\n{text.strip() or '(no output)'}"),
            meta={"exit_code": r.exit_code},
        )
