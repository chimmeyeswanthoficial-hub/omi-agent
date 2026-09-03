"""Git checkpoints — every mutation is snapshotted, so the UI can rewind."""

from __future__ import annotations

import re
import shlex

from ..runtime.base import Runtime

_GIT_ID = "-c user.email=agent@omi.local -c user.name=OmiAgent"
_REF_RE = re.compile(r"^[0-9a-f]{4,40}$")


async def ensure_git(rt: Runtime) -> None:
    r = await rt.exec(
        "git rev-parse --git-dir >/dev/null 2>&1 || "
        f"(git init -q && git add -A && git {_GIT_ID} commit -qm 'init: workspace baseline')"
    )
    if not r.ok:
        # no git binary? snapshots degrade to disabled — loop must not die on it
        return


async def snapshot(rt: Runtime, message: str) -> str | None:
    msg = shlex.quote(message[:120])
    r = await rt.exec(
        f"git add -A && git diff --cached --quiet || git {_GIT_ID} commit -qm {msg}; "
        "git rev-parse --short HEAD"
    )
    if not r.ok:
        return None
    for line in reversed(r.stdout.strip().splitlines()):
        if _REF_RE.match(line.strip()):
            return line.strip()
    return None


async def rewind(rt: Runtime, ref: str) -> bool:
    if not _REF_RE.match(ref or ""):
        return False
    r = await rt.exec(f"git reset --hard {shlex.quote(ref)} && git clean -fd -e '*.db'")
    return r.ok
