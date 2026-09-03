from __future__ import annotations

from typing import Any

from ..runtime.base import Runtime
from .base import Tool, ToolResult, apply_hunks, parse_patch, truncate, unified


class ApplyPatchTool(Tool):
    spec = {
        "name": "apply_patch",
        "description": "Apply a unified diff (multi-file). Headers '--- a/<path>' / '+++ b/<path>' with @@ hunks. "
        "Refuses to apply when hunk context does not match — nothing partial ever lands.",
        "args": {"patch": "string — unified diff text"},
    }

    async def run(self, rt: Runtime, args: dict[str, Any]) -> ToolResult:
        patch = args.get("patch")
        if not isinstance(patch, str) or not patch.strip():
            return ToolResult(ok=False, text="apply_patch: missing `patch` (unified diff string)")
        try:
            ops = parse_patch(patch)
        except Exception as e:  # noqa: BLE001
            return ToolResult(ok=False, text=f"apply_patch: cannot parse diff: {e}")
        if not ops:
            return ToolResult(
                ok=False, text="apply_patch: no valid file hunks found (need +++ b/<path> headers)"
            )
        reports, mutated = [], []
        for path, hunks in ops.items():
            try:
                old = await rt.read_file(path)
            except FileNotFoundError:
                old = ""
            except PermissionError as e:
                return ToolResult(ok=False, text=f"apply_patch: {e}")
            try:
                new = apply_hunks(old, hunks)
            except ValueError as e:
                return ToolResult(
                    ok=False,
                    text=f"apply_patch REJECTED ({path}): {e}. Re-read the file; context drifted.",
                )
            await rt.write_file(path, new)
            mutated.append(path)
            reports.append(truncate(unified(old, new, path), 1500))
        return ToolResult(
            ok=True,
            text=f"patched {len(mutated)} file(s): {', '.join(mutated)}\n\n" + "\n\n".join(reports),
            meta={"paths": mutated, "mutated": True},
        )
