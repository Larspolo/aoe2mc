"""Live replay: the live and lost military units of each type of each player (#3695)."""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
import units  # noqa: E402
from test_replay import Fake, data  # noqa: E402


class Census(Fake):
    """A fake server: `alive` holds the live count of each (player, type ID)."""

    def __init__(self, alive):
        super().__init__()
        self.alive = alive

    def command(self, cmd):
        super().command(cmd)
        m = re.fullmatch(rf"execute if entity @e\[tag={replay.COUNTED},tag=aoe2mc\.p(\d)(?:,tag=aoe2mc\.t(\d+))?\]", cmd)
        if not m:
            return ""
        n = sum(v for (p, t), v in self.alive.items() if p == int(m[1]) and (m[2] is None or t == int(m[2])))
        return f"Test passed. Count: {n}" if n else "Test failed"


def unit(name, player, k):
    return {"kind": "unit", "name": name, "player": player, "uuid": f"u{k}", "ref": k, "tile": [3.5, 3.5]}


def test_census_counts_each_military_type():
    ids = units.type_ids()
    d = data([])
    d["objects"] += [unit("KNIGHT", 1, 1), unit("KNIGHT", 1, 2), unit("ARCHER", 1, 3), unit("KNIGHT", 2, 4),
                     unit("VILLAGER_MALE", 1, 5), unit("SHEEP", 1, 6)]
    game = Census({(1, ids["KNIGHT"]): 2, (1, ids["ARCHER"]): 1, (2, ids["KNIGHT"]): 1})
    r = replay.Replay(game, d, ai=True)
    r.census()
    assert r.troops == {1: {"KNIGHT": 2, "ARCHER": 1}, 2: {"KNIGHT": 1}} and r.fallen == {}
    game.alive[(1, ids["KNIGHT"])] = 1
    r.census()
    assert r.troops[1] == {"KNIGHT": 1, "ARCHER": 1} and r.fallen[1] == {"KNIGHT": 1}
    assert r.troops[2] == {"KNIGHT": 1} and 2 not in r.fallen


def test_a_dead_type_is_not_counted_again():
    ids = units.type_ids()
    d = data([])
    d["objects"] += [unit("ARCHER", 1, 3)]
    game = Census({(1, ids["ARCHER"]): 1})
    r = replay.Replay(game, d, ai=True)
    r.census()
    game.alive.clear()
    r.census()
    assert r.troops[1] == {"ARCHER": 0} and r.fallen[1] == {"ARCHER": 1}
    game.sent.clear()
    r.census()
    assert not any(f"aoe2mc.t{ids['ARCHER']}" in c for c in game.sent)
