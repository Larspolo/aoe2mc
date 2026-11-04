"""#5662 (epic #5119): the game program runs the XS map script of the world (aoe2mc.json "xs_script")."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import scenario  # noqa: E402
from test_scenario_mode import game  # noqa: E402

SCRIPT = """int n = 0;
void main() { n = n + 1; xsChatData("start %d", n); }
rule r active minInterval 1 { xsChatData("rule"); }
"""


def run(script):
    server, g, _ = game({"0": {}, "1": {}, "2": {}})
    if script is not None:
        g.data["xs_script"] = ["m.xs", script]
    now = [0.0]
    g.clock, g.t0 = (lambda: now[0]), 0.0
    scenario.setup(g, "scenario")
    before = len(server.log)
    for t in (1.0, 5.0):
        now[0] = t
        scenario.tick(g)
    return g, server.log[before:]


def test_main_runs_once_and_the_rule_runs():
    g, log = run(SCRIPT)
    assert g.xs.get("n") == 1
    chats = [c for c in log if c.startswith("tellraw @a")]
    assert sum("start 1" in c for c in chats) == 1 and any('"rule"' in c for c in chats)


def test_no_script_no_xs():
    g, log = run(None)
    assert g.xs is None and not any("start" in c or "rule" in c for c in log)


def test_a_syntax_error_gives_one_warning(capsys):
    g, _ = run("void main( {")
    err = capsys.readouterr().err
    assert g.xs is None and err.count("XS script") == 1
