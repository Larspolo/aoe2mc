"""#5663 (epic #5119): the trigger effect "Script Call" sets a score of aoe_xs; the game program runs its XS code."""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import scenario  # noqa: E402
from test_scenario_mode import game  # noqa: E402
from test_trigger_objects import effect, trig  # noqa: E402

import aoe2mc  # noqa: E402


def call(code):
    return dict(effect(aoe2mc.XS_EFFECT), message=code)


def test_the_effect_sets_a_score_and_the_list_has_its_index():
    load, files = aoe2mc.trigger_files([trig([call(""), call("main();")])], stats=Counter())
    assert "scoreboard players set #x7.1 aoe_xs 1" in files["data/aoe2mc/function/trigger/7.mcfunction"]
    assert "#x7.0" not in files["data/aoe2mc/function/trigger/7.mcfunction"]
    assert "scoreboard objectives add aoe_xs dummy" in load
    assert aoe2mc.xs_list([trig([call(""), call("main();")])]) == [
        {"trigger": 7, "kind": "effect", "index": 1, "code": "main();"}]


def run(entries, fired, script=None):
    """A game with the "xs" entries; the scores in fired are 1. Two ticks of one game second each."""
    server, g, _ = game({"0": {}, "1": {}, "2": {}})
    g.data["xs"] = entries
    if script is not None:
        g.data["xs_script"] = ["m.xs", script]
    now, scores, command = [0.0], {s: 1 for s in fired}, g.command

    def answer(cmd):
        p = cmd.split()
        if p[:3] == ["scoreboard", "players", "get"] and p[4] in ("aoe_xs", "aoe_var"):
            return f"{p[3]} has {scores.get((p[3], p[4]), 0)} [{p[4]}]"
        if p[:3] == ["scoreboard", "players", "set"] and p[4] in ("aoe_xs", "aoe_var"):
            scores[(p[3], p[4])] = int(p[5])
        return command(cmd)
    g.command, g.clock, g.t0 = answer, (lambda: now[0]), 0.0
    scenario.setup(g, "scenario")
    for t in (1.0, 2.5):
        now[0] = t
        scenario.tick(g)
    return g, scores


def entry(i, code):
    return {"trigger": 3, "kind": "effect", "index": i, "code": code}


def test_a_fired_call_runs_once_and_the_score_goes_back_to_0():
    _, scores = run([entry(0, "xsSetTriggerVariable(4, xsTriggerVariable(4) + 5);")], [("#x3.0", "aoe_xs")])
    assert scores[("#v4", "aoe_var")] == 5 and scores[("#x3.0", "aoe_xs")] == 0


def test_whole_code_runs_its_first_function_with_the_map_script():
    script = "int n = 2;\n"
    g, scores = run([entry(1, "void f() { n = n + 1; xsSetTriggerVariable(1, n); }")], [("#x3.1", "aoe_xs")], script)
    assert g.xs.get("n") == 3 and scores[("#v1", "aoe_var")] == 3


def test_an_unknown_name_gives_one_warning_and_the_other_effects_run(capsys):
    _, scores = run([entry(0, "noSuchFunction(1);"), entry(1, "xsSetTriggerVariable(2, 7);")],
                    [("#x3.0", "aoe_xs"), ("#x3.1", "aoe_xs")])
    err = capsys.readouterr().err
    assert scores[("#v2", "aoe_var")] == 7 and err.count("noSuchFunction") == 1


def test_a_score_that_is_not_set_runs_nothing():
    _, scores = run([entry(0, "xsSetTriggerVariable(4, 5);")], [])
    assert ("#v4", "aoe_var") not in scores
