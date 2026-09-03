"""Persistence: per-task JSONL event log + meta sidecar + task listing."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .events import Event


class TaskStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # -- paths ---------------------------------------------------------
    def dir(self, task_id: str) -> Path:
        return self.root / task_id

    def _events_path(self, task_id: str) -> Path:
        return self.dir(task_id) / "events.jsonl"

    def _meta_path(self, task_id: str) -> Path:
        return self.dir(task_id) / "meta.json"

    # -- events --------------------------------------------------------
    def create(self, task_id: str, meta: dict[str, Any]) -> None:
        self.dir(task_id).mkdir(parents=True, exist_ok=True)
        meta.setdefault("created", time.time())
        self.save_meta(task_id, meta)
        self._events_path(task_id).touch(exist_ok=True)

    def append(self, task_id: str, ev: Event) -> None:
        with self._events_path(task_id).open("a", encoding="utf-8") as f:
            f.write(json.dumps(ev.to_dict(), ensure_ascii=False) + "\n")

    def read_events(self, task_id: str) -> list[Event]:
        p = self._events_path(task_id)
        if not p.is_file():
            return []
        out = []
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    out.append(Event.from_dict(json.loads(line)))
                except json.JSONDecodeError:
                    continue
        return out

    # -- meta ----------------------------------------------------------
    def save_meta(self, task_id: str, meta: dict[str, Any]) -> None:
        self._meta_path(task_id).write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def load_meta(self, task_id: str) -> dict[str, Any] | None:
        p = self._meta_path(task_id)
        if not p.is_file():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def update_meta(self, task_id: str, **fields: Any) -> dict[str, Any] | None:
        meta = self.load_meta(task_id) or {}
        meta.update(fields)
        self.save_meta(task_id, meta)
        return meta

    def list(self) -> list[dict[str, Any]]:
        out = []
        for d in sorted(self.root.iterdir(), reverse=True) if self.root.is_dir() else []:
            if d.is_dir() and (d / "meta.json").is_file():
                try:
                    out.append(json.loads((d / "meta.json").read_text(encoding="utf-8")))
                except json.JSONDecodeError:
                    continue
        return sorted(out, key=lambda m: m.get("created", 0), reverse=True)
