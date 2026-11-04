"""xs_mc: XS functions with parameters, return values, static locals and const (#5691)."""
import sys

from test_xs_mc_control import call

import xs
import xs_mc

sys.path.insert(0, "game")
import xs_run  # noqa: E402

SCRIPT = """
const int K = 3;
int calls = 0; int a = 0; int b = 0; int c = 0; int d = 0; int s = 0;
int add(int x = 0, int y = 0) { calls = calls + 1; return (x + y * K); }
int count() { static int n = 0; n++; return (n); }
bool big(int v = 0) { if (v > 10) { return (true); } return (false); }
int loop(int m = 0) { for (i = 0; < 100) { if (i * i >= m) { return (i); } } return (-1); }
void main() {
    a = add(2, 5) + add(1, 1) * 2;
    b = (a > 100) && big(add(a, 0));
    c = (a > 1) && big(a);
    d = (a > 1) || big(add(1, 1));
    count(); count(); s = count() + loop(50);
}
"""


def test_values_are_those_of_the_game_program():
    files, _, _, warnings = xs_mc.compile(xs.parse(SCRIPT), SCRIPT)
    assert warnings == []
    scores = {}
    call(files, "aoe2mc:xs/main", scores)
    want = xs_run.Xs(SCRIPT, out=lambda t: None)
    want.tick(0)
    for name in ("calls", "a", "b", "c", "d", "s"):
        assert scores.get((f"#g.{name}", xs_mc.OBJ), 0) == int(want.get(name)), name


def test_recursion_gives_one_warning():
    text = """int n = 0; int r = 0;
int fact(int v = 0) { if (v <= 1) { return (1); } return (v * fact(v - 1)); }
int one() { return (1); }
void main() { r = fact(3); n = one(); }"""
    files, _, _, warnings = xs_mc.compile(xs.parse(text), text)
    assert len(warnings) == 1 and "fact" in warnings[0]
    scores = {}
    call(files, "aoe2mc:xs/main", scores)
    assert scores[("#g.n", xs_mc.OBJ)] == 1
