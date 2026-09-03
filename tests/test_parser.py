from __future__ import annotations

from omiagent.agent.parser import parse_action


def test_plain_json_action():
    a = parse_action('{"thought": "look", "action": {"tool": "bash", "args": {"cmd": "ls"}}}')
    assert a.tool == "bash" and a.args["cmd"] == "ls" and a.thought == "look"


def test_fenced_json():
    a = parse_action(
        'Sure!\n```json\n{"thought":"t","action":{"tool":"read_file","args":{"path":"x.py"}}}\n```'
    )
    assert a.tool == "read_file" and a.args["path"] == "x.py"


def test_nested_braces_in_strings_survive():
    a = parse_action(
        '{"thought":"edit dict","action":{"tool":"edit_file",'
        '"args":{"path":"a.py","find":"d = {}","replace":"d = {1: 2}"}}}'
    )
    assert (
        a.tool == "edit_file" and a.args["find"] == "d = {}" and a.args["replace"] == "d = {1: 2}"
    )


def test_prose_before_json():
    a = parse_action(
        'I will run this now. {"thought":"go","action":{"tool":"bash","args":{"cmd":"echo 1"}}}'
    )
    assert a.tool == "bash"


def test_garbage_degrades_to_chat_answer():
    a = parse_action("the function is broken because it subtracts instead of adds")
    assert a.tool == "finish"
    assert "subtracts" in a.args["summary"]


def test_flat_action_without_wrapper():
    a = parse_action('{"thought":"x","tool":"search","args":{"pattern":"foo"}}')
    assert a.tool == "search" and a.args["pattern"] == "foo"
