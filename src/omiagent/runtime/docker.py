"""Docker sandbox runtime: per-task container, workspace bind mount, no sockets.

The agent's `bash`/edits run inside `<OMI_SANDBOX_IMAGE>`; the container sees
only /workspace. No docker.sock, no host FS, capped CPU/memory.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from .base import ExecResult, Runtime

_FALLBACK_IMAGE = "python:3.12-slim"


class DockerRuntime(Runtime):
    kind = "docker"

    def __init__(self, container, ws: Path) -> None:  # noqa: ANN001
        self._c = container
        self.ws = ws

    @classmethod
    async def start(
        cls, workspace: Path, *, image: str = "", sandbox_id: str = "omi"
    ) -> DockerRuntime:
        def _start() -> DockerRuntime:
            import docker

            client = docker.from_env()
            client.ping()
            try:
                client.images.get(image or "")
                img = image
            except Exception:  # noqa: BLE001 — custom image not built yet
                img = _FALLBACK_IMAGE
            name = f"omi-sbx-{sandbox_id}"
            # replace a stale container from a crashed run
            try:
                client.containers.get(name).remove(force=True)
            except Exception:  # noqa: BLE001
                pass
            c = client.containers.run(
                img,
                command=["sleep", "infinity"],
                detach=True,
                name=name,
                working_dir="/workspace",
                volumes={str(workspace): {"bind": "/workspace", "mode": "rw"}},
                mem_limit="1g",
                cpus=2.0,
                labels={"omiagent": "sandbox"},
            )
            return cls(c, workspace)

        return await asyncio.to_thread(_start)

    async def exec(self, cmd: str, timeout: float = 120.0) -> ExecResult:
        def _run() -> tuple[int, bytes, bytes]:
            res = self._c.exec_run(
                ["bash", "-lc", cmd], workdir="/workspace", demux=True, stdout=True, stderr=True
            )
            out, err = res.output if isinstance(res.output, tuple) else (res.output, None)
            return res.exit_code, out or b"", err or b""

        try:
            code, out, err = await asyncio.wait_for(asyncio.to_thread(_run), timeout=timeout)
        except TimeoutError:
            return ExecResult(exit_code=124, stderr=f"timeout after {timeout:.0f}s")
        except Exception as e:  # noqa: BLE001
            return ExecResult(exit_code=125, stderr=f"docker exec failed: {e}")
        return ExecResult(
            exit_code=code,
            stdout=out.decode("utf-8", "replace"),
            stderr=err.decode("utf-8", "replace"),
        )

    async def read_file(self, path: str) -> str:
        r = await self.run_python(
            f"import sys;sys.stdout.write(open({path!r},encoding='utf-8',errors='replace').read())"
        )
        if not r.ok:
            raise FileNotFoundError(f"no such file in workspace: {path}")
        return r.stdout

    async def write_file(self, path: str, content: str) -> None:
        import base64

        b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
        r = await self.run_python(
            "import base64,os;"
            f"p={path!r};os.makedirs(os.path.dirname(p) or '.',exist_ok=True);"
            f"open(p,'w',encoding='utf-8').write(base64.b64decode({b64!r}).decode('utf-8'))"
        )
        if not r.ok:
            raise RuntimeError(f"write failed: {r.stderr or r.stdout}")

    async def close(self) -> None:
        try:
            await asyncio.to_thread(lambda: self._c.remove(force=True))
        except Exception:  # noqa: BLE001 — best effort cleanup
            pass
