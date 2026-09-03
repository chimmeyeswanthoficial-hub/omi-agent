"""Context assembly: repo map + verify-command detection. Token-frugal by design."""

from __future__ import annotations

import json

from ..runtime.base import Runtime

_LIST_CODE = """
import os, json
skip = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".pytest_cache", ".ruff_cache", ".omi"}
out = []
for root, dirs, files in os.walk('.'):
    dirs[:] = sorted(d for d in dirs if d not in skip)
    if root.count(os.sep) >= 3:
        dirs[:] = []
    for fn in sorted(files):
        p = os.path.join(root, fn)
        try:
            out.append([p[2:], os.path.getsize(p)])
        except OSError:
            pass
        if len(out) >= 400:
            break
    if len(out) >= 400:
        break
print(json.dumps(out))
"""


async def build_repo_map(rt: Runtime) -> str:
    r = await rt.run_python(_LIST_CODE, timeout=30)
    if not r.ok:
        return "(repo map unavailable)"
    try:
        entries = json.loads(r.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return "(repo map unavailable)"
    lines = [
        f"{p}  ({sz} B)" if sz < 1024 else f"{p}  ({sz // 1024} KB)" for p, sz in entries[:180]
    ]
    more = "" if len(entries) <= 180 else f"\n… {len(entries) - 180} more files (use search/read)"
    return "## Repo map (paths + size, depth ≤ 3)\n" + "\n".join(lines) + more


_DETECT_VERIFY = """
import os, json
ok_pytest = False
try:
    import pytest  # noqa
    ok_pytest = os.path.exists("pytest.ini") or os.path.isdir("tests") or os.path.exists("pyproject.toml") \
        or any(f.endswith("_test.py") for f in os.listdir(".") if os.path.isfile(f))
except ImportError:
    pass
npm_test = False
try:
    with open("package.json") as f:
        npm_test = "test" in json.load(f).get("scripts", {})
except Exception:
    pass
cmd = "python3 -m pytest -q" if ok_pytest else ("npm test --silent" if npm_test else "")
print(cmd)
"""


async def detect_verify(rt: Runtime) -> str | None:
    r = await rt.run_python(_DETECT_VERIFY, timeout=20)
    if r.ok:
        for line in reversed(r.stdout.strip().splitlines()):
            if line.strip():
                return line.strip()
    return None
