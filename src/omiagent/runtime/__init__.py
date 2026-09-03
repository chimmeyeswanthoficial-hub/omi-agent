"""Execution runtimes: where agent commands actually run."""

from __future__ import annotations

from pathlib import Path

from .base import ExecResult, Runtime


async def create_runtime(mode: str, workspace: Path, *, image: str = "", sandbox_id: str = "omi"):
    """auto → Docker when the daemon is usable, else the local jail."""
    workspace = Path(workspace).resolve()
    if mode in ("auto", "docker"):
        try:
            from .docker import DockerRuntime

            rt = await DockerRuntime.start(workspace, image=image, sandbox_id=sandbox_id)
            return rt
        except Exception as e:  # noqa: BLE001
            if mode == "docker":
                raise RuntimeError(f"docker sandbox requested but unavailable: {e}") from e
    from .local import LocalRuntime

    return LocalRuntime(workspace)


__all__ = ["ExecResult", "Runtime", "create_runtime"]
