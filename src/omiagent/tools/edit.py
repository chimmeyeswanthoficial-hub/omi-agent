from __future__ import annotations

from typing import Any

from ..runtime.base import Runtime
from .base import Tool, ToolResult, unified


def _fuzzy_replace(old: str, find: str, replace: str) -> tuple[str, int] | None:
    """Match `find` ignoring trailing whitespace per line; only if unique."""
    o_lines = old.split("\n")
    f_lines = find.rstrip("\n").split("\n")
    if not f_lines:
        return None
    pat = [ln.rstrip() for ln in f_lines]
    cand = [
        i
        for i in range(len(o_lines) - len(pat) + 1)
        if [ln.rstrip() for ln in o_lines[i : i + len(pat)]] == pat
    ]
    if len(cand) != 1:
        return None
    i = cand[0]
    new_lines = o_lines[:i] + replace.split("\n") + o_lines[i + len(f_lines) :]
    return "\n".join(new_lines), 1


class EditFileTool(Tool):
    spec = {
        "name": "edit_file",
        "description": "Replace an exact snippet in a file. `find` must match verbatim (include a couple of context "
        "lines). If it does not match, nothing is written — re-read the file and copy the EXACT text.",
        "args": {
            "path": "string — workspace-relative",
            "find": "string — exact text to replace",
            "replace": "string — new text",
            "count": "int, optional — replace N occurrences (default 1; ambiguous matches are refused)",
        },
    }

    async def run(self, rt: Runtime, args: dict[str, Any]) -> ToolResult:
        path = str(args.get("path", "")).strip()
        find, replace = args.get("find"), args.get("replace")
        if not path or not isinstance(find, str) or not isinstance(replace, str) or not find:
            return ToolResult(
                ok=False, text="edit_file: needs `path`, non-empty `find`, string `replace`"
            )
        try:
            count = max(1, int(args.get("count") or 1))
        except (TypeError, ValueError):
            count = 1

        old = await rt.read_file(path)
        exact = old.count(find)
        if exact == 0:
            fuzzy = _fuzzy_replace(old, find, replace)
            if fuzzy is None:
                return ToolResult(ok=False, text=self._miss_report(path, old, find))
            new, n = fuzzy
        else:
            if count == 1 and exact > 1:
                return ToolResult(
                    ok=False,
                    text=f"edit_file: `find` matches {exact}x in {path}; add context lines or pass count={exact}",
                )
            n = min(count, exact)
            new = old.replace(find, replace, n)
        if new == old:
            return ToolResult(ok=False, text="edit_file: replacement identical to original (no-op)")
        await rt.write_file(path, new)
        return ToolResult(
            ok=True,
            text=f"edited {path} ({n} replacement(s))\n{unified(old, new, path)[:3500]}",
            meta={"path": path, "mutated": True},
        )

    @staticmethod
    def _miss_report(path: str, old: str, find: str) -> str:
        words = [w for w in find.strip().split() if len(w) > 3][:3]
        hint = ""
        if words:
            near = [
                f"  {i + 1}: {ln.strip()[:90]}"
                for i, ln in enumerate(old.split("\n"))
                if any(w in ln for w in words)
            ][:5]
            if near:
                hint = "\nlines sharing your words:\n" + "\n".join(near)
        return (
            f"edit_file: `find` not found in {path}. Re-read the file and copy the EXACT text "
            f"(whitespace and indentation matter).{hint}"
        )
