from __future__ import annotations

import pytest

from omiagent.config import ProviderCfg, ProvidersCfg
from omiagent.gateway.audit import UsageLog
from omiagent.gateway.router import ChatResult, GatewayError, MaxRouter, classify
from tests.conftest import make_cfg, scripted_router


def _msgs(text: str):
    return [{"role": "user", "content": text}]


def test_classify_groups():
    assert classify(_msgs("fix the bug please")) == "code-edit"
    assert classify(_msgs("```\nold\n```\n```\nnew\n```")) == "code-edit"
    assert classify(_msgs("what is the capital of France")) == "shell-debug"
    assert (
        classify(_msgs("plan the refactor architecture")) == "code-edit"
    )  # "refactor" wins over "plan"
    assert classify(_msgs("why does this design deadlock? analyse it")) == "plan-reason"
    assert classify(_msgs("hi")) == "shell-debug"
    assert (
        classify([{"role": "user", "content": [{"type": "image_url", "image_url": {"url": "x"}}]}])
        == "vision"
    )
    assert classify(_msgs("x" * 70_000)) == "long-context"
    assert classify(_msgs("anything"), "plan-reason") == "plan-reason"  # hint wins


async def test_chat_records_usage_and_routes(clean_env):
    router, calls = scripted_router(
        ['{"thought":"t","action":{"tool":"bash","args":{"cmd":"true"}}}']
    )
    res = await router.chat(_msgs("fix bug x"), caller="test")
    assert res.text.startswith('{"thought"')
    assert res.provider == "alpha"
    assert res.group in ("code-edit", "shell-debug")
    assert calls[0]["provider"] == "alpha"


async def test_chain_skips_keyless_providers(monkeypatch, clean_env):
    cfg = ProvidersCfg(
        providers=[
            ProviderCfg(name="needs-key", model="x/y", api_key_env="GROQ_API_KEY"),
            ProviderCfg(name="no-key-needed", model="z/w"),
        ],
        groups={"default": ["needs-key", "no-key-needed"]},
    )

    async def complete(dep, messages, temperature):
        return ChatResult(text="ok", tokens_in=1, tokens_out=1)

    r = MaxRouter(cfg, complete=complete)
    res = await r.chat(_msgs("anything"))
    assert res.provider == "no-key-needed"  # needs-key has no env var → skipped
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    r2 = MaxRouter(cfg, complete=complete)
    res2 = await r2.chat(_msgs("anything"))
    assert res2.provider == "needs-key"  # now first by priority (100 vs 100, input order)


async def test_fallback_walks_chain_and_cooldowns(clean_env):
    n = {"i": 0}

    async def flaky(dep, messages, temperature):
        n["i"] += 1
        if dep.name == "alpha":
            raise RuntimeError("HTTP 429 rate limit")
        return ChatResult(text="from-beta", tokens_in=2, tokens_out=2)

    router = MaxRouter(make_cfg("alpha", "beta"), complete=flaky)
    res = await router.chat(_msgs("hello there"))
    assert res.provider == "beta"
    assert (
        router.in_cooldown("alpha") is False or True
    )  # one failure counts; two cools — check below

    res2 = await router.chat(_msgs("again"))  # alpha failed 2nd time → cooled
    assert res2.provider == "beta"
    assert router.in_cooldown("alpha"), "second consecutive failure should start cooldown"


async def test_all_fail_raises(clean_env):
    async def always_bad(dep, messages, temperature):
        raise RuntimeError("boom 500")

    router = MaxRouter(make_cfg("alpha", "beta"), complete=always_bad)
    with pytest.raises(GatewayError):
        await router.chat(_msgs("hi"))


async def test_no_providers_at_all(clean_env):
    router = MaxRouter(ProvidersCfg(), complete=None)
    with pytest.raises(GatewayError, match="no providers"):
        await router.chat(_msgs("hi"))


async def test_usage_log(tmp_path):
    log = UsageLog(tmp_path / "usage.db")
    log.record(
        task_id="t1",
        caller="test",
        group="code-edit",
        provider="p",
        model="m",
        tokens_in=100,
        tokens_out=50,
        usd=0.01,
        elapsed_ms=5,
    )
    log.record(
        task_id="t1",
        caller="test",
        group="shell-debug",
        provider="p",
        model="m",
        tokens_in=10,
        tokens_out=5,
        usd=0.02,
        elapsed_ms=5,
    )
    t = log.totals_for("t1")
    assert t["tokens_in"] == 110 and abs(t["usd"] - 0.03) < 1e-9
    assert log.totals_for("nope")["calls"] == 0
    assert log.totals()["calls"] == 2
