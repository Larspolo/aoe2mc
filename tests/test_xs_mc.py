"""xs_mc: the int globals and main() of an XS script as datapack functions (#5689)."""
import json
import re
import sys

import pytest

import xs
import xs_mc

sys.path.insert(0, "game")
import xs_run  # noqa: E402

SCRIPT = """
int a = -7;
int b = 2;
bool less = false;
int q = 0; int r = 0; int s = 0; int p = 0; int d = 0; int e = 0;
void main() {
    q = a / b; r = a % b; s = a + b; d = b - a; p = a * b;
    e = (0 - a) / (0 - b) + 7 % (0 - b) * 10;
    less = a < b;
    xsSetTriggerVariable(3, q * 100 + r);
    xsChatData("q is %d", q);
}
"""


def run(lines, scores):
    """A small model of the scoreboard commands of xs_mc."""
    def get(h, o):
        return scores.get((h, o), 0)

    def test(conds):
        for neg, h, o, rest in re.findall(r"(if|unless) score (\S+) (\S+) (matches \S+|\S+ \S+ \S+)", conds):
            if rest.startswith("matches"):
                lo, _, hi = rest.split()[1].partition("..")
                v = get(h, o)
                ok = (not lo or v >= int(lo)) and (not hi or v <= int(hi)) if ".." in rest else v == int(lo)
            else:
                op, h2, o2 = rest.split()
                a, b = get(h, o), get(h2, o2)
                ok = {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b, "=": a == b}[op]
            if ok != (neg == "if"):
                return False
        return True

    for line in lines:
        if m := re.match(r"execute store success score (\S+) (\S+) (.*)", line):
            scores[m[1], m[2]] = int(test(m[3]))
            continue
        if m := re.match(r"execute (.*?) run (.*)", line):
            if not test(m[1]):
                continue
            line = m[2]
        w = line.split()
        if w[:3] == ["scoreboard", "players", "set"]:
            scores[w[3], w[4]] = int(w[5])
        elif w[:3] in (["scoreboard", "players", "add"], ["scoreboard", "players", "remove"]):
            scores[w[3], w[4]] = get(w[3], w[4]) + int(w[5]) * (1 if w[2] == "add" else -1)
        elif w[:3] == ["scoreboard", "players", "operation"]:
            t, op, v = (w[3], w[4]), w[5], get(w[6], w[7])
            a = get(*t)
            if op in ("/=", "%=") and v == 0:
                continue
            scores[t] = {"=": v, "+=": a + v, "-=": a - v, "*=": a * v, "/=": a // v if v else a, "%=": a % v if v else a}[op]
        elif w[0] == "tellraw":
            scores.setdefault("chat", []).append(json.loads(line.split(" ", 2)[2]))
        else:
            raise AssertionError(line)


def compiled(text):
    files, tick, load, warnings = xs_mc.compile(xs.parse(text), text)
    return files[f"{xs_mc.DIR}/main.mcfunction"].splitlines(), tick, load, warnings


def test_scores_are_those_of_the_game_program():
    lines, tick, load, warnings = compiled(SCRIPT)
    assert warnings == [] and tick == [xs_mc.TICK] and load == xs_mc.LOAD
    scores = {}
    run(lines, scores)
    want = xs_run.Xs(SCRIPT, out=lambda t: None)
    want.tick(0)
    for name in "abqrspde":
        assert scores[f"#g.{name}", xs_mc.OBJ] == want.get(name), name
    assert scores["#g.less", xs_mc.OBJ] == int(want.get("less")) == 1
    assert scores["#v3", xs_mc.VAR] == want.get("q") * 100 + want.get("r") == -301
    assert scores["#main", xs_mc.OBJ] == 1
    assert scores["chat"][0][1] == "q is " and scores["chat"][0][2]["score"]["name"] == "#g.q"


@pytest.mark.parametrize("a,b", [(7, 2), (-7, 2), (7, -2), (-7, -2), (6, -3), (-6, 3), (5, 0)])
def test_division_truncates_toward_zero(a, b):
    text = f"int x = {a}; int y = {b}; int q = 0; int r = 0; void main() {{ q = x / y; r = x % y; }}"
    scores = {}
    run(compiled(text)[0], scores)
    q, r = (a, a) if b == 0 else (xs_run.binary("/", a, b), xs_run.binary("%", a, b))   # 0: the scores stay
    assert (scores["#g.q", xs_mc.OBJ], scores["#g.r", xs_mc.OBJ]) == (q, r)


def test_sin_gives_one_warning_and_the_rest_compiles():
    text = "int a = 1;\nvoid main() {\n  a = 5;\n  a = sin(a);\n  a = a + 1;\n}\n"
    lines, _, _, warnings = compiled(text)
    assert warnings == ["XS script: sin (line 4): no datapack form, the game program runs it (game/run.py)"]
    scores = {}
    run(lines, scores)
    assert scores["#g.a", xs_mc.OBJ] == 6


@pytest.mark.parametrize("script", [None, ["map", "int a = 2; void main() { xsSetTriggerVariable(1, a); }"]])
def test_world_gets_xs_files_only_with_a_script(tmp_path, script):
    import numpy as np

    import aoe2mc
    aoe2mc.write_datapack(str(tmp_path), [], np.zeros((8, 8), int), xs_script=script)
    pack = tmp_path / "datapacks" / "aoe2mc" / "data"
    fns = sorted(p.name for p in (pack / "aoe2mc" / "function" / "xs").glob("*")) if script else []
    assert (pack / "aoe2mc" / "function" / "xs").exists() == bool(script)
    tag = pack / "minecraft" / "tags" / "function" / "tick.json"
    ticks = json.loads(tag.read_text())["values"] if tag.exists() else []
    assert ("aoe2mc:xs/tick" in ticks) == bool(script)
    if script:
        assert fns == ["main.mcfunction", "tick.mcfunction"]
        assert (pack / "aoe2mc" / "function" / "load.mcfunction").read_text().startswith(xs_mc.LOAD[0])
