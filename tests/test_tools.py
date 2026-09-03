from __future__ import annotations

import difflib

from omiagent.tools import execute


async def test_bash_ok_and_policy(rt):
    ok = await execute("bash", {"cmd": "echo omi > out.txt && cat out.txt"}, rt)
    assert ok.ok and "omi" in ok.text
    blocked = await execute("bash", {"cmd": "sudo rm -rf /"}, rt)
    assert not blocked.ok and "policy" in blocked.text


async def test_bash_unknown_exit_code(rt):
    r = await execute("bash", {"cmd": "exit 3"}, rt)
    assert not r.ok and "[exit 3]" in r.text


async def test_read_write_roundtrip(rt):
    w = await execute("write_file", {"path": "pkg/new.py", "content": "x = 1\ny = 2\n"}, rt)
    assert w.ok and "created" in w.text
    rd = await execute("read_file", {"path": "pkg/new.py"}, rt)
    assert "1: x = 1" in rd.text


async def test_read_offset_and_truncation(rt):
    content = "\n".join(f"line{i}" for i in range(1, 501))
    await execute("write_file", {"path": "big.txt", "content": content}, rt)
    r = await execute("read_file", {"path": "big.txt", "offset": 400, "limit": 5}, rt)
    assert "400: line400" in r.text and "more lines" in r.text


async def test_edit_exact_fuzzy_and_ambiguous(rt):
    r = await execute(
        "edit_file",
        {"path": "hello.py", "find": "return f'hi {name}   '", "replace": "return f'hello {name}'"},
        rt,
    )
    assert r.ok and "edited hello.py" in r.text
    content = await rt.read_file("hello.py")
    assert "hello {name}" in content

    amb = await execute("write_file", {"path": "dup.txt", "content": "same\nsame\n"}, rt)
    assert amb.ok
    bad = await execute("edit_file", {"path": "dup.txt", "find": "same", "replace": "diff"}, rt)
    assert not bad.ok and "matches 2x" in bad.text

    miss = await execute(
        "edit_file", {"path": "hello.py", "find": "def nonexistent_zzz(", "replace": "x"}, rt
    )
    assert not miss.ok and "not found" in miss.text


async def test_search(rt):
    await execute("write_file", {"path": "s/a.py", "content": "def target_fn():\n    pass\n"}, rt)
    r = await execute("search", {"pattern": "target_fn", "glob": "*.py"}, rt)
    assert r.ok and "s/a.py:1:" in r.text
    none = await execute("search", {"pattern": "nope_xyz", "glob": "*.py"}, rt)
    assert none.ok and "no matches" in none.text


async def test_apply_patch(rt):
    old = await rt.read_file("hello.py")
    new = old.replace("hi {name}", "yo {name}")
    diff = "\n".join(
        difflib.unified_diff(
            old.splitlines(), new.splitlines(), "a/hello.py", "b/hello.py", lineterm=""
        )
    )
    r = await execute("apply_patch", {"patch": diff.replace("a/hello.py", "b/hello.py")}, rt)
    assert r.ok and "yo {name}" in await rt.read_file("hello.py")


async def test_patch_rejects_drifted_context(rt):
    bad = "+++ b/hello.py\n@@ -1,2 +1,2 @@\n-context that does not exist\n+whatever\n"
    r = await execute("apply_patch", {"patch": bad}, rt)
    assert not r.ok and "REJECTED" in r.text


async def test_unknown_tool_and_finish_spec(rt):
    r = await execute("does_not_exist", {}, rt)
    assert not r.ok and "unknown tool" in r.text
