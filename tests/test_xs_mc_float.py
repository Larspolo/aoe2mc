"""xs_mc: float and vector values as fixed point scores, with the math and vector functions (#5694)."""
import sys

import pytest
from test_xs_mc_control import call

import xs
import xs_mc

sys.path.insert(0, "game")
import xs_run  # noqa: E402

SCRIPT = """
float a = 2.75; float b = -1.5; float big = 100.0; float big2 = 0.0;
float sum = 0.0; float dif = 0.0; float pro = 0.0; float quo = 0.0; float neg = 0.0; float mixed = 0.0;
float fa = 0.0; float ff = 0.0; float fc = 0.0; float fr = 0.0; float fr2 = 0.0; float fs = 0.0; float fs2 = 0.0;
float fp = 0.0; float fp2 = 0.0; float fdeg = 0.0; float frad = 0.0; float fd = 0.0; float fl = 0.0;
float gx = 0.0; float gy = 0.0; float gz = 0.0; float nx = 0.0; float ny = 0.0; float nz = 0.0;
int ci = 0; int ti = 0; int tn = 0; bool less = false; float inc = 0.5;
vector v = vector(3.0, 4.0, 0.0); vector w = cVectorZero; vector u = vector(0.0, 0.0, 0.0);
void main() {
    big2 = big * big;
    sum = a + b; dif = a - b; pro = a * b; quo = a / b; neg = -a; mixed = a * 2 + 1;
    fa = abs(b); ff = floor(b); fc = ceil(a); fr = round(a + 0.01); fr2 = round(1.2345, 2);
    ci = xsCeilToInt(b); ti = a; tn = b; less = b < a; inc++;
    fs = sqrt(2.0); fs2 = sqrt(12345.678); fp = pow(b, 3); fp2 = pow(2.0, -2);
    fdeg = degrees(1.25); frad = radians(135.0);
    w = xsVectorSet(1.0, -2.0, 2.0);
    fd = dist(v, w); fl = xsVectorLength(v);
    u = xsVectorNormalize(v * 2.5 - w);
    w = xsVectorSetY(w, 7.25); w = xsVectorSetX(w, a); w = xsVectorSetZ(w, -0.5);
    gx = xsVectorGetX(w); gy = xsVectorGetY(w); gz = xsVectorGetZ(w);
    nx = xsVectorGetX(u); ny = xsVectorGetY(u); nz = xsVectorGetZ(u);
}
"""


def scores_of(text):
    files, _, _, warnings = xs_mc.compile(xs.parse(text), text)
    scores = {}
    call(files, "aoe2mc:xs/main", scores)
    return scores, warnings


def test_values_are_those_of_the_game_program():
    text = SCRIPT.replace("cVectorZero", "vector(0.0, 0.0, 0.0)")
    scores, warnings = scores_of(text)
    assert warnings == []
    want = xs_run.Xs(text, out=lambda t: None)
    want.tick(0)
    names = xs_run_names(text)
    assert len(names) > 30
    for name, typ in names:
        w = want.get(name)
        if typ == "vector":
            got = [scores[f"#g.{name}.{c}", xs_mc.OBJ] / 1000 for c in "xyz"]
            assert got == pytest.approx(list(w), abs=0.002), name
        elif typ == "float":
            assert scores[f"#g.{name}", xs_mc.OBJ] / 1000 == pytest.approx(w, abs=0.002), name
        else:
            assert scores[f"#g.{name}", xs_mc.OBJ] == int(w), name


def xs_run_names(text):
    return [(n[2], n[1]) for n in xs.parse(text) if n[0] == "var"]


def test_product_of_two_hundreds_does_not_overflow():
    scores, _ = scores_of("float a = 100.0; float p = 0.0; void main() { p = a * a; }")
    assert scores["#g.p", xs_mc.OBJ] == 10000000


def test_trigonometry_keeps_the_warning_line():
    scores, warnings = scores_of("float a = 1.0;\nvoid main() {\n  a = sin(a);\n  a = a + 1.0;\n}\n")
    assert warnings == ["XS script: sin (line 3): no datapack form, the game program runs it (game/run.py)"]
    assert scores["#g.a", xs_mc.OBJ] == 2000
