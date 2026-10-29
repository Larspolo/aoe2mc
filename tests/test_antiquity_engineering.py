"""Engineering of Antiquity Mode (#3981): the siege units and the ships get +2 range and +2 tiles of line of sight
(attack sight and exploration), as in Return of Rome. The rule modules read their data at import, so the check runs
in one child process."""
import json

from test_antiquity_setting import child

CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from test_fog_seen import T, bare, circle
from game import combat, train
out = {}
for n in ("STONE_THROWER", "BALLISTA", "WAR_GALLEY", "HOPLITE"):
    s = combat.stats(n)
    more = train.sight_more({"ENGINEERING"}, n, s)
    out[n] = [train.TECHS["ENGINEERING"](n, s).range - s.range, more,
              combat.sight_command("u", n, 1, more=more), combat.sight(n)]
def tiles(techs):
    g = bare()
    g.soldiers, g.techs = {"b": "BALLISTA"}, set(techs)
    return g.seen_tiles({"b": (40.5 * T, 70.0, 40.5 * T)})
r = combat.sight("BALLISTA")
before, after = tiles(()), tiles({"ENGINEERING"})
out["seen"] = [(40 + r + 1, 40) in before, circle(40, 40, r + 2) <= after, (40 + r + 3, 40) in after]
print(json.dumps(out))
'''


def test_engineering_adds_2_range_and_sight_to_siege_and_ships():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    for n in ("STONE_THROWER", "BALLISTA", "WAR_GALLEY"):
        plus, more, cmd, sight = out[n]
        assert (plus, more) == (2, 2), n
        assert cmd.split()[3] == str(sight + 2), n
    assert out["HOPLITE"][:2] == [0, 0]
    assert out["HOPLITE"][2].split()[3] == str(out["HOPLITE"][3])
    assert out["seen"] == [False, True, False]
