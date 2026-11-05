"""#5796: the Script Calls of a converted scenario run also in the modes that are not `scenario`."""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
from test_scenario_mode import game  # noqa: E402


def test_a_fired_script_call_runs_in_the_mode_standard():
    _, g, _ = game({"0": {}, "1": {}, "2": {}})
    g.mode, g.bots = "standard", []
    g.data["xs"] = [{"trigger": 3, "kind": "effect", "index": 0,
                     "code": "xsSetTriggerVariable(4, xsTriggerVariable(4) + 5);"}]
    scores, command = {("#x3.0", "aoe_xs"): 1}, g.command

    def answer(cmd):
        p = cmd.split()
        if p[:3] == ["scoreboard", "players", "get"] and p[4] in ("aoe_xs", "aoe_var"):
            return f"{p[3]} has {scores.get((p[3], p[4]), 0)} [{p[4]}]"
        if p[:3] == ["scoreboard", "players", "set"] and p[4] in ("aoe_xs", "aoe_var"):
            scores[(p[3], p[4])] = int(p[5])
        return command(cmd)
    g.command, end = answer, time.monotonic() + 30
    g.run(until=lambda: scores.get(("#v4", "aoe_var")) or time.monotonic() > end)
    assert scores[("#v4", "aoe_var")] == 5 and scores[("#x3.0", "aoe_xs")] == 0

