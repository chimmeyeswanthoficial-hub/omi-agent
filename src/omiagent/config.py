"""Configuration: environment (OMI_* vars / .env) + providers routing yaml."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderCfg(BaseModel):
    """One callable model deployment behind the `max` virtual model."""

    name: str
    model: str  # litellm-style: "gemini/gemini-2.5-flash", "openrouter/qwen/..."
    api_key_env: str | None = None
    tags: list[str] = Field(default_factory=list)
    priority: int = 100


class RouterTuning(BaseModel):
    cooldown_s: float = 45.0
    max_retries: int = 2
    classify: Literal["heuristic", "task-header"] = "heuristic"


class ProvidersCfg(BaseModel):
    providers: list[ProviderCfg] = Field(default_factory=list)
    groups: dict[str, list[str]] = Field(default_factory=dict)
    router: RouterTuning = Field(default_factory=RouterTuning)

    @classmethod
    def load(cls, path: str | Path) -> ProvidersCfg:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return cls.model_validate(data)

    def provider(self, name: str) -> ProviderCfg | None:
        return next((p for p in self.providers if p.name == name), None)

    def chain(self, group: str) -> list[ProviderCfg]:
        """Ordered, key-available deployments for a task group."""

        names = self.groups.get(group) or self.groups.get("default") or []
        out: list[ProviderCfg] = []
        for n in names:
            p = self.provider(n)
            if p and has_key(p):
                out.append(p)
        if group != "default" and not out:  # widen before giving up
            out = [p for p in self.providers if has_key(p)]
        return sorted(out, key=lambda p: p.priority)

    def available(self) -> list[ProviderCfg]:
        return [p for p in self.providers if has_key(p)]


def has_key(p: ProviderCfg) -> bool:
    """Provider usable if it needs no key or the env var is non-empty."""
    import os

    if not p.api_key_env:
        return True
    return bool(os.environ.get(p.api_key_env, "").strip())


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OMI_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    host: str = "127.0.0.1"
    port: int = 8000
    data_dir: Path = Path("~/.omi")
    workspaces_dir: Path = Path("~/omi-workspaces")
    sandbox: Literal["auto", "docker", "local"] = "auto"
    sandbox_image: str = "omiagent/runtime:local"
    max_steps: int = 80
    step_timeout_s: int = 120
    task_budget_usd: float = 1.00
    providers_file: str = "configs/providers.yaml"
    gateway_key: str | None = None
    static_dir: str | None = None  # serve built UI (defaults to ./ui/dist)
    plan_approval_timeout_s: int = 25  # auto-continue so tasks never hang

    @property
    def resolved_static_dir(self) -> Path | None:
        if self.static_dir:
            p = Path(self.static_dir).expanduser()
            return p if p.is_dir() else None
        guess = Path(__file__).resolve().parents[2] / "ui" / "dist"
        return guess if guess.is_dir() else None

    @property
    def providers(self) -> ProvidersCfg:
        path = Path(self.providers_file).expanduser()
        if not path.is_file():  # fall back to in-repo default
            path = Path(__file__).resolve().parents[2] / "configs" / "providers.yaml"
        if not path.is_file():
            return ProvidersCfg()
        return ProvidersCfg.load(path)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.data_dir = Path(s.data_dir).expanduser()
    s.workspaces_dir = Path(s.workspaces_dir).expanduser()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    s.workspaces_dir.mkdir(parents=True, exist_ok=True)
    return s
