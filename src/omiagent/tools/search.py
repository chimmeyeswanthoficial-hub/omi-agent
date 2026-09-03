from __future__ import annotations

from typing import Any

from ..runtime.base import Runtime
from .base import Tool, ToolResult, truncate

_SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".pytest_cache",
    ".ruff_cache",
}
_SKIP_SUFFIX = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".gz", ".lock"}


class SearchTool(Tool):
    spec = {
        "name": "search",
        "description": "Regex search over text files in the workspace. Returns path:line: content, capped at `limit`.",
        "args": {
            "pattern": "string — python regex",
            "glob": "string, optional — filename glob (e.g. '*.py')",
            "limit": "int, optional — default 60",
        },
    }

    async def run(self, rt: Runtime, args: dict[str, Any]) -> ToolResult:
        pattern = str(args.get("pattern", ""))
        if not pattern:
            return ToolResult(ok=False, text="search: missing `pattern`")
        try:
            limit = min(200, max(1, int(args.get("limit") or 60)))
        except (TypeError, ValueError):
            limit = 60
        glob = str(args.get("glob") or "*")
        # executed INSIDE the runtime so docker/local behave identically
        code = f"""
import os, re, sys
pat = re.compile({pattern!r})
skip = {_SKIP_DIRS!r}
suf = {_SKIP_SUFFIX!r}
hits = []
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in skip and not d.startswith('.')]
    for fn in files:
        if not fnmatch.fnmatch(fn, {glob!r}) or any(fn.endswith(s) for s in suf):
            continue
        p = os.path.join(root, fn)
        try:
            with open(p, encoding='utf-8') as fh:
                for i, line in enumerate(fh, 1):
                    if pat.search(line):
                        hits.append(f"{{p[2:]}}:{{i}}: {{line.rstrip()[:160]}}")
                        if len(hits) >= {limit + 1}:
                            break
        except (UnicodeDecodeError, OSError):
            continue
    if len(hits) > {limit}:
        break
print("\\n".join(hits[:{limit}]))
if len(hits) > {limit}:
    print(f"(+{{len(hits) - limit}} more — refine pattern/glob)")
"""
        r = await rt.run_python(f"import fnmatch\n{code}", timeout=45)
        if not r.ok:
            return ToolResult(ok=False, text=f"search failed: {truncate(r.stderr, 500)}")
        out = r.stdout.strip()
        if not out:
            return ToolResult(ok=True, text=f"no matches for /{pattern}/ in {glob}")
        return ToolResult(ok=True, text=truncate(out))
