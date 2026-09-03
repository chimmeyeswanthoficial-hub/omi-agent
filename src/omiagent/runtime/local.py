"""Local jail: for machines without Docker. Path-jailed, env-stripped, timed.

Security is weaker than a container (same kernel, same user) — docs/security.md
says so out loud. The denylist policy + this jail + timeouts are the mitigations.
"""

from __future__ import annotations

import asyncio
import os
import signal
from pathlib import Path

from .base import ExecResult, Runtime

_ENV_KEEP = ("PATH", "LANG", "TERM", "TMPDIR", "HOME", "USER")


class LocalRuntime(Runtime):
    kind = "local"

    def __init__(self, workspace: Path) -> None:
        self.ws = Path(workspace).resolve()
        self.ws.mkdir(parents=True, exist_ok=True)

    # -- paths -----------------------------------------------------------
    def _resolve(self, path: str) -> Path:
        p = (self.ws / path).resolve()
        if not str(p).startswith(str(self.ws) + os.sep) and p != self.ws:
            raise PermissionError(f"path escapes workspace jail: {path!r}")
        return p

    # -- exec ------------------------------------------------------------
    async def exec(self, cmd: str, timeout: float = 120.0) -> ExecResult:
        env = {k: v for k, v in os.environ.items() if k in _ENV_KEEP}
        env["HOME"] = str(self.ws)  # keep caches dotfiles inside the jail
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                cwd=str(self.ws),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,
            )
        except OSError as e:
            return ExecResult(exit_code=127, stderr=f"spawn failed: {e}")
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except TimeoutError:
            _kill_group(proc)
            return ExecResult(
                exit_code=124, stderr=f"timeout after {timeout:.0f}s (process killed)"
            )
        return ExecResult(
            exit_code=proc.returncode if proc.returncode is not None else 1,
            stdout=out.decode("utf-8", "replace"),
            stderr=err.decode("utf-8", "replace"),
        )

    # -- files -------------------------------------------------------------
    async def read_file(self, path: str) -> str:
        p = self._resolve(path)
        if not p.is_file():
            raise FileNotFoundError(f"no such file in workspace: {path}")
        return p.read_text(encoding="utf-8", errors="replace")

    async def write_file(self, path: str, content: str) -> None:
        p = self._resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def _kill_group(proc: asyncio.subprocess.Process) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        try:
            proc.kill()
        except ProcessLookupError:
            pass
