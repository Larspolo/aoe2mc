"""A saved game keeps the state of its XS script: variables, statics, rule states and times; no main() again (#5665)."""
import json
from types import SimpleNamespace

from game import savegame
from game.xs_run import Xs

SRC = """
int count = 0;
const int LIMIT = 9;
vector spot = vector(1, 2, 3);
int mains = 0;
void main() { mains = mains + 1; }
rule counter minInterval 1 maxInterval 5 { static int n = 0; n = n + 1; count = count + 1; spot = vector(n, 0, 0); }
rule once minInterval 1 { xsDisableSelf(); }
"""


def game(x):
    return SimpleNamespace(xs=x)


def test_round_trip():
    a = Xs(SRC, out=print)
    for t in (0, 1, 2):
        a.tick(t)
    d = json.loads(json.dumps({"xs": savegame.xs_state(a)}))
    b = Xs(SRC, out=print)
    savegame.xs_again(game(b), d)
    assert b.get("count") == a.get("count") == 2 and b.get("spot") == a.get("spot") == (2.0, 0.0, 0.0)
    assert b.statics == a.statics and b.started
    for n in ("counter", "once"):
        assert {k: b.rules[n][k] for k in savegame.XS_RULE} == {k: a.rules[n][k] for k in savegame.XS_RULE}
    assert not b.rules["once"]["on"]
    b.tick(3)
    assert b.get("mains") == 1 and b.get("count") == 3


def test_no_script_no_key():
    from test_repair_siege import setup
    g = setup()[1]
    assert "xs" not in savegame.dump(g)
    g.xs = Xs(SRC, out=print)
    g.xs.tick(0)
    d = json.loads(json.dumps(savegame.dump(g)))
    assert d["xs"]["started"] and "LIMIT" not in d["xs"]["globals"]
    b = Xs(SRC, out=print)
    savegame.xs_again(game(b), {})                              # an older save: no change
    assert not b.started
