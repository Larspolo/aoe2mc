"""xs_mc: the XS rules and the rule functions as datapack functions (#5692)."""
import re
import sys

from test_xs_mc import run
from test_xs_mc_control import call, cond

import xs
import xs_mc

sys.path.insert(0, "game")
import xs_run  # noqa: E402

SCRIPT = """
int a = 0; int b = 0; int c = 0; int d = 0; int t = 0; int t2 = 0; bool on = false;
rule two active minInterval 2 { a = a + 1; t = xsGetTime() / 1000; t2 = xsGetGameTime(); }
rule late inactive { b = b + 1; on = xsIsRuleGroupEnabled("g"); }
rule g1 inactive group g highFrequency { c = c + 1; if (c >= 10) { xsDisableSelf(); } }
rule g2 inactive group g runImmediately priority 5 { d = d + 1; xsDisableRuleGroup("g"); xsEnableRule("g1"); }
void main() { xsEnableRule("late"); xsEnableRuleGroup("g"); }
"""


def ticks(files, tick, n):
    """Run n ticks with the score model; one player is online."""
    scores = {}
    for _ in range(n):
        for line in tick:
            if line == xs_mc.TICK:
                if scores.get(("#main", xs_mc.OBJ)) != 1:
                    call(files, "aoe2mc:xs/main", scores)
                continue
            if m := re.match(r"(execute .*) run function (\S+)$", line):
                probe = {k: v for k, v in scores.items() if k != "chat"}
                if cond(m[1], probe):
                    call(files, m[2], scores)
                continue
            run([line], scores)
    return scores


def test_rule_runs_are_those_of_the_game_program():
    files, tick, _, warnings = xs_mc.compile(xs.parse(SCRIPT), SCRIPT)
    assert warnings == []
    scores = ticks(files, tick, 100)
    want = xs_run.Xs(SCRIPT, out=lambda t: None)
    for k in range(100):
        want.tick(k / 20)
    for name in "abcdt":
        assert scores[f"#g.{name}", xs_mc.OBJ] == want.get(name), name
    assert scores["#g.t2", xs_mc.OBJ] == 4          # xsGetGameTime: a host function of the game program
    assert scores["#g.on", xs_mc.OBJ] == int(want.get("on"))
    assert (scores["#g.a", xs_mc.OBJ], scores["#g.b", xs_mc.OBJ], scores["#g.d", xs_mc.OBJ]) == (2, 4, 1)


def test_computed_rule_name_gives_one_warning():
    text = 'rule r inactive { }\nvoid main() {\n  string s = "r";\n  xsEnableRule(s);\n}\n'
    warnings = xs_mc.compile(xs.parse(text), text)[3]
    assert [w for w in warnings if "xsEnableRule" in w] == [
        "XS script: xsEnableRule (line 4): no datapack form, the game program runs it (game/run.py)"]


def test_set_rule_priority_gives_one_warning():
    text = "rule r { xsSetRulePriority(\"r\", 3); }\n"
    assert xs_mc.compile(xs.parse(text), text)[3] == [
        "XS script: xsSetRulePriority (line 1): no datapack form, the game program runs it (game/run.py)"]
