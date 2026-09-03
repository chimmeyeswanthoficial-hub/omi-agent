from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from omiagent.config import ProviderCfg, ProvidersCfg  # noqa: E402
from omiagent.gateway.router import ChatResult, MaxRouter  # noqa: E402
from omiagent.runtime.local import LocalRuntime  # noqa: E402


@pytest.fixture
def rt(tmp_path) -> LocalRuntime:
    (tmp_path / "hello.py").write_text(
        "def greet(name):\n    return f'hi {name}   '\n", encoding="utf-8"
    )
    return LocalRuntime(tmp_path)


def make_cfg(*names: str) -> ProvidersCfg:
    return ProvidersCfg(
        providers=[ProviderCfg(name=n, model=f"fake/{n}") for n in names],
        groups={
            g: list(names)
            for g in (
                "code-edit",
                "shell-debug",
                "plan-reason",
                "long-context",
                "vision",
                "default",
            )
        },
    )


def scripted_router(replies: list[str], fail: int = 0) -> tuple[MaxRouter, list[dict]]:
    """Router whose 'provider' pops scripted replies; records calls; optional first-N failures."""
    calls: list[dict] = []

    async def complete(dep: ProviderCfg, messages: list[dict], temperature: float) -> ChatResult:
        calls.append({"provider": dep.name})
        i = len(calls) - 1
        if fail and i < fail and len(replies) > 1:
            raise RuntimeError("429 rate limit exceeded")
        text = replies[min(i, len(replies) - 1)]
        return ChatResult(text=text, tokens_in=10, tokens_out=5, usd=0.001)

    return MaxRouter(make_cfg("alpha", "beta"), complete=complete), calls


@pytest.fixture
def clean_env(monkeypatch):
    for v in (
        "GEMINI_API_KEY",
        "OPENROUTER_API_KEY",
        "DEEPSEEK_API_KEY",
        "GROQ_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    ):
        monkeypatch.delenv(v, raising=False)
