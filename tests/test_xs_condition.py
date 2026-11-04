"""#5664 (epic #5119): the trigger condition "Script Call" tests a score of aoe_xs; the game program calls its XS
function once per game second and sets the score."""
from collections import Counter

from test_trigger_objects import effect, trig
from test_xs_effect import run

import aoe2mc


def cond(code):
    return {"type": aoe2mc.SCRIPT_CALL, "xs": code, "inverted": False}


def test_the_condition_tests_the_score_of_its_index():
    t = dict(trig([effect(aoe2mc.XS_EFFECT) | {"message": "main();"}]), conditions=[cond("bool c() { return (true); }")])
    load, files = aoe2mc.trigger_files([t], stats=Counter())
    assert any("if score #c7.0 aoe_xs matches 1" in f for f in files.values())
    assert "scoreboard objectives add aoe_xs dummy" in load
    assert aoe2mc.xs_list([t])[0] == {"trigger": 7, "kind": "condition", "index": 0, "code": t["conditions"][0]["xs"]}


def entry(code):
    return {"trigger": 3, "kind": "condition", "index": 0, "code": code}


def test_the_score_follows_the_game_time(monkeypatch):
    import recap
    now = [0]
    monkeypatch.setattr(recap, "game_time", lambda g: now[0])
    g, scores = run([entry("bool c() { return (xsGetGameTime() > 5); }")], [])
    assert scores[("#c3.0", "aoe_xs")] == 0
    import scenario
    now[0], g.xs_cond_at = 6, 0.0
    scenario.conditions(g)
    assert scores[("#c3.0", "aoe_xs")] == 1


def test_a_runtime_error_gives_one_warning_and_the_score_0(capsys):
    _, scores = run([entry("bool c() { int a = 0; return (1 / a > 0); }")], [])
    assert scores[("#c3.0", "aoe_xs")] == 0
    assert capsys.readouterr().err.count("runtime error") == 1
