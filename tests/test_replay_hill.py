"""Live replay of a King of the Hill record: the monument changes its owner by the units near it (#4893). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import gather  # noqa: E402
import hill  # noqa: E402
import replay  # noqa: E402
import wonder  # noqa: E402
from test_replay import Fake, data  # noqa: E402


def game(kind, monument=(8.0, 8.0)):
    d = data([])
    d["lobby"] = {"type": kind}
    d["objects"].append({"kind": "building", "name": "MONUMENT", "player": 0, "tile": list(monument)})
    return replay.Replay(Fake(), d)


def put(r, i, player, tile):
    v = gather.Villager(f"u{i}", (tile[0] * r.T, 64.0, tile[1] * r.T))
    v.player = player
    r.units[i] = v


def test_units_of_player_2_alone_near_the_monument_make_it_its_own():
    r = game(replay.KING_OF_THE_HILL)
    put(r, 1, 2, (9.0, 8.0))
    put(r, 2, 1, (8.0 + hill.REACH + 3, 8.0))                       # out of reach
    cmds = r.hill_check(60000)
    assert r.hill["owner"] == 2 and any(hill.BAR in c and "monument" in c for c in cmds)
    put(r, 3, 1, (8.0, 8.5))                                         # the owner keeps it while its unit is near
    r.hill_check(70000)
    assert r.hill["owner"] == 2 and r.hill["left"] == hill.YEARS * wonder.YEAR - 10
    r.units.pop(1)
    r.hill_check(80000)
    assert r.hill["owner"] == 1
    assert any("King of the Hill" in c for c in r.summary_commands())


def test_a_random_map_record_has_no_monument_rules():
    r = game("Random Map")
    put(r, 1, 2, (8.0, 8.0))
    assert r.hill is None and r.hill_check(60000) == []
    assert not any("King of the Hill" in c for c in r.summary_commands())
