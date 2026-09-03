"""Runtime contract shared by docker + local jails.

File access goes through the runtime too, so tool behavior is identical
whether commands run in a container or in the jailed local directory.
"""

from __future__ import annotations

import base64
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class ExecResult:
    exit_code: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.exit_code == 0

    def tail(self, n: int = 4000) -> str:
        out = (
            self.stdout
            if len(self.stdout) >= len(self.stderr)
            else self.stdout + (f"\n[stderr]\n{self.stderr}" if self.stderr else "")
        )
        return (
            out
            if len(out) <= n
            else out[: n // 2] + f"\n…[truncated {len(out) - n} chars]…\n" + out[-n // 2 :]
        )


class Runtime(ABC):
    kind: str = "base"

    @abstractmethod
    async def exec(self, cmd: str, timeout: float = 120.0) -> ExecResult: ...

    @abstractmethod
    async def read_file(self, path: str) -> str: ...

    @abstractmethod
    async def write_file(self, path: str, content: str) -> None: ...

    async def run_python(self, code: str, timeout: float = 60.0) -> ExecResult:
        """Run a python snippet in the sandbox (used for listing/patching)."""
        b64 = base64.b64encode(code.encode("utf-8")).decode("ascii")
        return await self.exec(
            f"python3 -c \"import base64;exec(base64.b64decode('{b64}').decode())\"", timeout
        )

    async def close(self) -> None:  # pragma: no cover - default no-op
        return None
