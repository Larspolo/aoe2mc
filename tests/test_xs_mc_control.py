"""xs_mc: if, else, while, for, break, continue and switch as datapack sub-functions (#5690)."""
import re
import sys

import pytest
from test_xs_mc import run

import xs
import xs_mc

sys.path.insert(0, "game")
import xs_run  # noqa: E402

SCRIPT = """
int sum = 0; int n = 0; int odd = 0; int sw = 0; int sw2 = 0; int big = 0; int nest = 0;
void main() {
    for (i = 0; < 10) { sum = sum + i; }
    while (true) { n = n + 1; if (n % 2 == 0) { continue; } odd = odd + n; if (n >= 9) { break; } }
    for (k = 5; > 0) {
        switch (k) {
            case 1: sw = sw + 1;
            case 2: { sw = sw + 20; break; }
            case 3: sw = sw + 300; break;
            default: sw = sw + 4000;
        }
        if (k == 2) { continue; } else { sw2 = sw2 + k; }
    }
    switch (7) { case 1: big = 1; }
    if (sum > 100) big = 2; else if (sum > 40) big = 3; else big = 4;
    for (a = 0; < 4) { for (b = 0; < 4) { if (b > a) break; nest = nest + 1; } }
}
"""


def call(files, name, scores):
    """Run a function of files with the model of test_xs_mc, with `function` and `return`."""
    lines = files[f"{xs_mc.DIR}/{name.split('/', 1)[1]}.mcfunction"].splitlines()
    for line in lines:
        m = re.match(r"(?:(execute .*?) run )?(function \S+|return(?: run (.*)| 0))$", line)
        if not m:
            run([line], scores)
            continue
        if m[1] and not cond(m[1], scores):
            continue
        if m[2].startswith("function"):
            call(files, m[2].split()[1], scores)
        else:
            if m[3]:
                run([m[3]], scores)
            return


def cond(text, scores):
    probe = {**{k: v for k, v in scores.items() if k != "chat"}}
    run([f"{text} run scoreboard players set #t probe 1"], probe)
    return probe.get(("#t", "probe")) == 1


def test_values_are_those_of_the_game_program():
    files, _, _, warnings = xs_mc.compile(xs.parse(SCRIPT), SCRIPT)
    assert warnings == []
    scores = {}
    call(files, "aoe2mc:xs/main", scores)
    want = xs_run.Xs(SCRIPT, out=lambda t: None)
    want.tick(0)
    for name in ("sum", "n", "odd", "sw", "sw2", "big", "nest"):
        assert scores.get((f"#g.{name}", xs_mc.OBJ), 0) == want.get(name), name


@pytest.mark.parametrize("text,part", [("void main() { break; }", "break"),
                                       ("int a = 0; void main() { while (a < 2) { a++; continue; } switch (a) { case 1: continue; } }", "continue")])
def test_break_outside_a_loop_gives_a_warning(text, part):
    assert [w.split(":")[1].split()[0] for w in xs_mc.compile(xs.parse(text), text)[3]] == [part]
