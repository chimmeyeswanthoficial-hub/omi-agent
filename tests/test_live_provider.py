"""First real provider call — the smoke test that proves your keys + routing.

Skipped by default (no keys in CI ⇒ skipif). To run it locally:

    set -a && . ./.env && set +a
    pytest -m live            # or: make live-test

Everything here makes at most a few tiny calls (~a few hundred tokens total).
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
KEY_VARS = (
    "GEMINI_API_KEY",
    "OPENROUTER_API_KEY",
    "DEEPSEEK_API_KEY",
    "GROQ_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
)
HAVE_KEYS = [k for k in KEY_VARS if os.environ.get(k, "").strip()]

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not HAVE_KEYS,
        reason=f"no provider keys in env — export one of: {', '.join(KEY_VARS)}",
    ),
]

CALL_TIMEOUT_S = 45.0


def _make_settings(tmp_path: Path):
    from omiagent.config import Settings

    return Settings(
        data_dir=Path(tempfile.mkdtemp()) / "d",
        workspaces_dir=Path(tempfile.mkdtemp()) / "w",
        providers_file=str(ROOT / "configs" / "providers.yaml"),
        sandbox="local",
        static_dir=str(tmp_path / "nostatic"),
    )


def _require_live_providers(settings) -> None:
    if not settings.providers.available():
        pytest.skip(
            "keys present but none match configs/providers.yaml api_key_env entries "
            "— export e.g. GEMINI_API_KEY before running"
        )


async def test_real_call_routes_records_and_answers(tmp_path):
    """Router path: heuristic classification → real provider → usage ledger rows."""
    from omiagent.gateway.audit import UsageLog
    from omiagent.gateway.router import MaxRouter

    settings = _make_settings(tmp_path)
    _require_live_providers(settings)
    usage = UsageLog(tmp_path / "usage.db")
    router = MaxRouter(settings.providers, usage=usage)

    res = await asyncio.wait_for(
        router.chat(
            [{"role": "user", "content": "Reply with exactly: OMI-OK"}],
            task_hint="shell-debug",
            caller="live-test",
        ),
        timeout=CALL_TIMEOUT_S,
    )
    assert res.text.strip(), "provider answered empty"
    assert res.provider and res.model and res.group == "shell-debug"
    totals = usage.totals()
    assert totals["calls"] >= 1
    assert totals["tokens_in"] + totals["tokens_out"] > 0, "provider reported no usage tokens"


async def test_heuristic_classification_reaches_a_sane_group(tmp_path):
    """No hint given: a code-edit style prompt should classify to code-edit (or widen)."""
    from omiagent.gateway.router import MaxRouter

    settings = _make_settings(tmp_path)
    _require_live_providers(settings)
    router = MaxRouter(settings.providers)
    res = await asyncio.wait_for(
        router.chat(
            [
                {
                    "role": "user",
                    "content": "fix this bug by editing the file:\n```python\nx = 1  # should be 2\n```",
                }
            ],
            caller="live-test",
        ),
        timeout=CALL_TIMEOUT_S,
    )
    assert res.group in {"code-edit", "shell-debug", "plan-reason", "long-context", "vision"}


async def test_v1_openai_compatible_shape(tmp_path):
    """Full HTTP surface: /v1/chat/completions returns OpenAI-shaped JSON incl. omi metadata."""
    import httpx

    from omiagent.server.app import create_app

    settings = _make_settings(tmp_path)
    _require_live_providers(settings)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings)),
        base_url="http://live",
        timeout=CALL_TIMEOUT_S,
    ) as c:
        r = await c.post(
            "/v1/chat/completions",
            json={"model": "max", "messages": [{"role": "user", "content": "Say exactly: PONG"}]},
        )
    assert r.status_code == 200, r.text[:400]
    body = r.json()
    assert body["model"] == "max"
    assert body["choices"][0]["message"]["content"].strip()
    assert body["usage"]["total_tokens"] > 0
    assert body["omi"]["provider"], "routing metadata missing"
