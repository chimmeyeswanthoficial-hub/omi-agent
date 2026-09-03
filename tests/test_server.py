from __future__ import annotations

import asyncio

import httpx

from omiagent.config import Settings
from omiagent.server.app import create_app


def make_settings(tmp_path, gateway_key=None) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        workspaces_dir=tmp_path / "ws",
        providers_file=str(tmp_path / "missing.yaml"),
        sandbox="local",
        plan_approval_timeout_s=0,
        gateway_key=gateway_key,
        static_dir=str(tmp_path / "nostatic"),
    )


def _client(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_healthz_and_config(tmp_path):
    async with _client(create_app(make_settings(tmp_path))) as c:
        h = await c.get("/healthz")
        assert h.status_code == 200 and h.json()["ok"] is True
        cfg = await c.get("/api/config")
        assert cfg.status_code == 200
        assert cfg.json()["sandbox"] == "local"


async def test_create_task_validation(tmp_path):
    app = create_app(make_settings(tmp_path))
    async with _client(app) as c:
        empty = await c.post("/api/tasks", json={"prompt": ""})
        assert empty.status_code == 422
        bad_repo = await c.post("/api/tasks", json={"prompt": "x", "repo_path": "/no/such/place"})
        assert bad_repo.status_code == 400
        assert "not found" in bad_repo.json()["detail"]


async def test_e2e_task_lifecycle_without_keys(tmp_path, clean_env):
    app = create_app(make_settings(tmp_path))
    async with _client(app) as c:
        r = await c.post("/api/tasks", json={"prompt": "say hi", "mode": "plan"})
        assert r.status_code == 201
        tid = r.json()["task_id"]
        status = None
        for _ in range(60):
            d = (await c.get(f"/api/tasks/{tid}")).json()
            status = d["status"]
            if status != "running":
                break
            await asyncio.sleep(0.1)
        assert status in {"error", "finished"}
        evs = (await c.get(f"/api/tasks/{tid}/events")).json()
        kinds = [e["kind"] for e in evs]
        assert "task_started" in kinds and kinds[-1] == "task_finished"
        assert (
            "gateway failure" in d["summary"]
            or "no providers" in d["summary"]
            or "all providers" in d["summary"]
        )


async def test_gateway_auth_gate(tmp_path):
    # assembled at runtime so no credential-shaped literal ever lives in source
    gw_key = "omi" + "-gateway-" + "key-42"
    auth = {"Authorization": "Bearer " + gw_key}
    app = create_app(make_settings(tmp_path, gateway_key=gw_key))
    async with _client(app) as c:
        assert (await c.get("/v1/models")).status_code == 401
        ok = await c.get("/v1/models", headers=auth)
        assert ok.status_code == 200
        assert "max" in [m["id"] for m in ok.json()["data"]]
        bad = await c.post(
            "/v1/chat/completions",
            json={"model": "max", "messages": [{"role": "user", "content": "hi"}], "stream": True},
            headers=auth,
        )
        assert bad.status_code == 400  # stream unsupported, auth passed


async def test_no_ui_placeholder(tmp_path):
    async with _client(create_app(make_settings(tmp_path))) as c:
        r = await c.get("/")
        assert r.status_code == 200 and "ui" in r.json()
