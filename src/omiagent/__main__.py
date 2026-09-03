"""CLI: `omiagent serve | demo | version`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="omiagent", description="OmiAgent — your own arena.ai/agent, self-hosted.")
    p.add_argument("--version", action="version", version=f"omiagent {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="run API + UI on http://host:port")
    s.add_argument("--host", default=None)
    s.add_argument("--port", type=int, default=None)

    d = sub.add_parser("demo", help="run one agent task from the terminal")
    d.add_argument("--repo", default="examples/demo_repo", help="path to the workspace repo")
    d.add_argument("--prompt", default="Make the failing tests pass and explain the bug you fixed.")
    d.add_argument("--mode", choices=["plan", "auto"], default="plan")
    d.add_argument("--fake", action="store_true", help="offline demo: scripted model, real tools")

    args = p.parse_args(argv)
    if args.cmd == "serve":
        return _serve(args)
    if args.cmd == "demo":
        return _demo(args)
    return 0


def _serve(args: argparse.Namespace) -> int:
    import uvicorn

    from .config import get_settings
    from .server.app import create_app

    settings = get_settings()
    host = args.host or settings.host
    port = args.port or settings.port
    prov = settings.providers.available()
    print(f"⚡ omiagent {__version__}")
    print(f"   UI + API  → http://{host}:{port}")
    print(f"   gateway   → POST http://{host}:{port}/v1/chat/completions (model='max')")
    if not prov:
        print("   ⚠ no provider keys found — copy .env.example → .env and set at least one key")
        print("     (offline demo without keys: `omiagent demo --fake`)")
    else:
        print(f"   providers → {', '.join(p.name for p in prov)}")
    uvicorn.run(create_app(settings), host=host, port=port)
    return 0


def _demo(args: argparse.Namespace) -> int:
    import asyncio
    import shutil
    import tempfile

    from .agent.loop import AgentLoop, LoopConfig
    from .gateway.router import MaxRouter
    from .runtime.local import LocalRuntime

    repo = Path(args.repo)
    if not repo.is_dir():
        print(f"demo repo not found: {repo.resolve()}", file=sys.stderr)
        return 2
    ws = Path(tempfile.mkdtemp(prefix="omigdemo-")) / "repo"
    shutil.copytree(repo, ws, ignore=shutil.ignore_patterns("__pycache__", ".venv"))
    rt = LocalRuntime(ws)

    if args.fake:
        router = _fake_router()
    else:
        from .config import get_settings

        router = MaxRouter(get_settings().providers)

    from . import events as E

    ICONS = {
        "task_started": "🚀",
        "plan_proposed": "🗺️ ",
        "plan_approved": "✅",
        "step_started": "──",
        "reasoning": "💭",
        "tool_call": "🔧",
        "tool_result": "   ↳",
        "verify": "🧪",
        "checkpoint": "📸",
        "cost": "💵",
        "error": "⚠️ ",
        "status": "ℹ️ ",
        "task_finished": "🏁",
    }

    async def emit(ev: E.Event) -> None:
        p = ev.payload
        if ev.kind == "plan_proposed":
            print("  " + "\n  ".join(f"• {s}" for s in p["steps"]))
        elif ev.kind == "tool_call":
            print(f"{ICONS[ev.kind]} {p['tool']}  {_one_line(p['args'])}")
        elif ev.kind == "tool_result":
            head = (p["text"] or "").splitlines()[0][:120] if p.get("text") else ""
            print(f"{ICONS[ev.kind]} {'ok' if p['ok'] else 'ERR'}  {head}")
        elif ev.kind == "cost":
            print(
                f"{ICONS[ev.kind]} {p['group']} → {p['provider']}  "
                f"{p['tokens_in']}↑ {p['tokens_out']}↓  ${p['usd']:.4f}"
            )
        elif ev.kind == "checkpoint":
            print(f"{ICONS[ev.kind]} {p['commit']}  {p['message']}")
        elif ev.kind in ("error",):
            print(f"{ICONS[ev.kind]} {p['message']}")
        elif ev.kind == "reasoning":
            print(f"{ICONS[ev.kind]} {_one_line(p['text'])}")
        elif ev.kind == "verify":
            print(f"{ICONS[ev.kind]} {'PASSED' if p['ok'] else 'FAILED'}")
        elif ev.kind == "task_finished":
            print(f"{ICONS[ev.kind]} [{p['status']}] {_one_line(p['summary'])}  ({p['steps']} steps, ${p['usd']:.4f})")
        else:
            print(f"{ICONS.get(ev.kind, '·')} {p.get('prompt') or p.get('message') or ''}")

    async def go() -> int:
        loop = AgentLoop(
            router=router,
            runtime=rt,
            emit=emit,
            task_id="demo",
            cfg=LoopConfig(plan_approval_timeout_s=0.1),
        )
        res = await loop.run(args.prompt, mode=args.mode)
        log = await rt.exec("git log --oneline | head -8")
        print("\n— workspace git log —\n" + log.stdout)
        shutil.rmtree(ws.parent, ignore_errors=True)
        return 0 if res.status == "finished" else 1

    print(f"demo workspace: {ws}\n")
    return asyncio.run(go())


def _one_line(s: str, n: int = 110) -> str:
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[:n] + "…"


def _fake_router():
    """Scripted provider for offline demos/tests — mirrors what a real model
    would emit for examples/demo_repo (one injected `add()` bug)."""
    import json

    from .config import ProviderCfg, ProvidersCfg
    from .gateway.router import ChatResult, MaxRouter

    cfg = ProvidersCfg(providers=[ProviderCfg(name="fake", model="fake/scripted")], groups={"default": ["fake"]})
    # NB: the first edit attempt is INTENTIONALLY naive — the tool refuses it
    # ("matches 2x"), and the retry with context lines shows off the feedback
    # loop that a real model rides on too.
    script = [
        json.dumps(
            {
                "plan": [
                    "reproduce with pytest",
                    "locate the bug in calculator.add",
                    "fix add() to return a + b",
                    "run pytest and confirm green",
                ]
            }
        ),
        json.dumps(
            {
                "thought": "reproduce failing tests",
                "action": {"tool": "bash", "args": {"cmd": "python3 -m pytest -q || true"}},
            }
        ),
        json.dumps(
            {
                "thought": "add() subtracts — wrong operator",
                "action": {
                    "tool": "edit_file",
                    "args": {
                        "path": "calculator.py",
                        "find": "return a - b",
                        "replace": "return a + b",
                    },
                },
            }
        ),
        json.dumps(
            {
                "thought": "ambiguous — target the BUG-commented line only",
                "action": {
                    "tool": "edit_file",
                    "args": {
                        "path": "calculator.py",
                        "find": "    return a - b  # BUG: should be a + b",
                        "replace": "    return a + b",
                    },
                },
            }
        ),
        json.dumps(
            {
                "thought": "bug fixed; loop verify will confirm",
                "action": {
                    "tool": "finish",
                    "args": {"summary": "calculator.add used '-' instead of '+'; fixed and tests pass."},
                },
            }
        ),
    ]
    idx = {"i": 0}

    async def fake_complete(dep, messages, temperature):
        i = min(idx["i"], len(script) - 1)
        idx["i"] += 1
        return ChatResult(text=script[i], tokens_in=40, tokens_out=30, usd=0.0)

    return MaxRouter(cfg, complete=fake_complete)


if __name__ == "__main__":
    raise SystemExit(main())
