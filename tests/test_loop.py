from __future__ import annotations

import asyncio
import json

from omiagent import events as E
from omiagent.agent.loop import AgentLoop, LoopConfig
from tests.conftest import scripted_router


def _j(thought, tool, **args):
    return json.dumps({"thought": thought, "action": {"tool": tool, "args": args}})


async def test_full_edit_and_finish_flow(rt, tmp_path):
    (tmp_path / "buggy.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    replies = [
        json.dumps({"plan": ["reproduce", "fix add", "verify"]}),
        _j("read first", "read_file", path="buggy.py"),
        _j(
            "subtract is wrong",
            "edit_file",
            path="buggy.py",
            find="return a - b",
            replace="return a + b",
        ),
        _j("done", "finish", summary="add() now sums"),
    ]
    router, _ = scripted_router(replies)
    seen: list[E.Event] = []

    async def emit(ev: E.Event) -> None:
        seen.append(ev)

    loop = AgentLoop(
        router=router,
        runtime=rt,
        emit=emit,
        cfg=LoopConfig(plan_approval_timeout_s=0, verify_cmd=None),
    )
    res = await loop.run("fix add() in buggy.py", mode="plan")
    assert res.status == "finished"
    assert "add() now sums" in res.summary
    assert "return a + b" in (tmp_path / "buggy.py").read_text(encoding="utf-8")
    kinds = [e.kind for e in seen]
    assert (
        "plan_proposed" in kinds
        and "plan_approved" in kinds
        and "reasoning" in kinds
        and "tool_result" in kinds
    )
    assert kinds[-1] == "task_finished"


async def test_checkpoint_created_after_mutation(rt, tmp_path):
    if (await rt.exec("git --version")).exit_code != 0:
        import pytest

        pytest.skip("git not available")
    replies = [
        _j("write a file", "write_file", path="note.md", content="# hi\n"),
        _j("done", "finish", summary="wrote note"),
    ]
    router, _ = scripted_router(replies)
    events: list[E.Event] = []

    async def emit(ev):
        events.append(ev)

    loop = AgentLoop(
        router=router,
        runtime=rt,
        emit=emit,
        cfg=LoopConfig(plan_approval_timeout_s=0, verify_cmd=None),
    )
    res = await loop.run("create note.md", mode="auto")
    assert res.status == "finished"
    assert any(e.kind == "checkpoint" for e in events), "mutation must snapshot"
    log = await rt.exec("git log --oneline | wc -l")
    assert int(log.stdout.strip()) >= 2  # baseline + checkpoint


async def test_malformed_model_reply_becomes_chat_answer(rt, tmp_path):
    router, _ = scripted_router(["plain conversational answer, no json at all"])
    received: list[E.Event] = []

    async def emit(ev):
        received.append(ev)

    loop = AgentLoop(
        router=router,
        runtime=rt,
        emit=emit,
        cfg=LoopConfig(verify_cmd=None, plan_approval_timeout_s=0),
    )
    res = await loop.run("just tell me about this repo", mode="auto")
    assert res.status == "finished"
    assert "conversational" in res.summary


async def test_unknown_tool_feedback_loops_back(rt, tmp_path):
    replies = [
        _j("try bogus", "teleport", dest="mars"),
        _j("ok finish instead", "finish", summary="aborted gracefully"),
    ]
    router, calls = scripted_router(replies)
    received: list[E.Event] = []

    async def emit(ev):
        received.append(ev)

    loop = AgentLoop(
        router=router,
        runtime=rt,
        emit=emit,
        cfg=LoopConfig(verify_cmd=None, plan_approval_timeout_s=0),
    )
    res = await loop.run("do the impossible", mode="auto")
    assert res.status == "finished" and len(calls) == 2
    errs = [e for e in received if e.kind == "tool_result" and not e.payload["ok"]]
    assert any("unknown tool" in e.payload["text"] for e in errs)


async def test_max_steps_cap(rt, tmp_path):
    loop_reply = _j("echo again", "bash", cmd="echo tick")
    router, _ = scripted_router([loop_reply])

    async def emit(ev):
        return None

    loop = AgentLoop(
        router=router, runtime=rt, emit=emit, cfg=LoopConfig(max_steps=3, verify_cmd=None)
    )
    res = await loop.run("loop forever please", mode="auto")
    assert res.status == "max-steps" and res.steps == 3


async def test_plan_approval_gate(rt, tmp_path):
    approved = asyncio.Event()
    replies = [
        json.dumps({"plan": ["a", "b"]}),
        _j("go", "bash", cmd="echo after-approval"),
        _j("done", "finish", summary="ok"),
    ]
    router, _ = scripted_router(replies)

    async def emit(ev):
        if ev.kind == "plan_proposed":
            approved.set()

    loop = AgentLoop(
        router=router,
        runtime=rt,
        emit=emit,
        cfg=LoopConfig(plan_approval_timeout_s=5, verify_cmd=None),
        approved=approved,
    )
    res = await loop.run("x", mode="plan")
    assert res.status == "finished"
