"""The live replay on Paper with an ORDER or a unit on a water cell: the replay goes on, and a walk takes the height of
the unit where the map has no ground (#3000). Fake RCON."""
import contextlib
import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_ai import MIL  # noqa: E402
from test_replay_spawn import REC  # noqa: E402
from test_replay_walk import VIL  # noqa: E402

import aoe2mc  # noqa: E402

N = 64
SEA = {(x, z) for x in range(N) for z in range(40, N)}        # the water south of z = 40 (ground cells, not tiles)
SHIP = dict(kind="unit", name="FISHING_SHIP", player=2, uuid="e2", ref=30, tile=[12.5, 10.0])   # next to the shore
LAND = dict(MIL, tile=[3.5, 2.5])                       # the militia on land (z < 40 is land)
DOCK = dict(kind="building", name="DOCK", player=2, ref=31, tile=[12.0, 11.0], footprint=[44, 40, 60, 48])


def on_paper(timeline, objects):
    d = data(timeline, n=N)
    d["ground"] = [" ".join("-" if (x, z) in SEA else "70" for x in range(N)) for z in range(N)]
    d["objects"] += objects
    now, game = [0.0], Fake()

    def sleep(s):
        now[0] += s
    r = replay.Replay(game, d, ai=True)
    r.run(speed=4.0, clock=lambda: now[0], sleep=sleep, log=None, finish=True)
    return r, game.sent


def test_an_order_on_an_enemy_ship_on_the_water_attacks_it():
    timeline = [dict(time=0, player=1, kind="order", objects=[8], target=30, tile=[12.5, 10.0])]
    _, sent = on_paper(timeline, [LAND, SHIP])
    assert "aoe attack u2 e2" in sent and not any("None" in c for c in sent)


def test_an_order_on_an_enemy_dock_on_the_water_attacks_its_footprint():
    timeline = [dict(time=0, player=1, kind="order", objects=[8], target=31, tile=[12.0, 11.0])]
    _, sent = on_paper(timeline, [LAND, DOCK])
    assert [c for c in sent if c.startswith("aoe attack u2 ")] and not any("None" in c for c in sent)


def test_a_land_unit_on_a_water_cell_walks_with_its_own_height():
    d = data([], n=N)
    d["ground"] = [" ".join("-" if (x, z) in SEA else "70" for x in range(N)) for z in range(N)]
    d["objects"] += [dict(VIL, tile=[12.5, 12.5])]                 # a walk on the water: no path, no ground
    r = replay.Replay(Fake(), d, ai=True)
    r.grid()
    v = r.units[7]
    y = v.pos[1]
    moves = [c.split() for c in r.go(7, v, None, [], 0) if c.startswith("aoe moveto u1 ")]
    assert len(moves) == 1 and float(moves[0][4]) == y


@pytest.mark.slow
def test_a_jump_into_the_sample_record_lake_plays_on(tmp_path):
    """The sample record to 7:00 with a jump of 1 minute at 5:00 (the lake of villager 9961): no TypeError."""
    pytest.importorskip("mgz.model")
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(REC, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        d = json.load(f)
    d["timeline"] = [e for e in d["timeline"] if e["time"] <= 7 * 60000]
    now, game, done = [0.0], Fake(), []

    def sleep(s):
        now[0] += s

    def poll(control):
        if control["time"] >= 300000 and not done:
            control["jump"] = control["time"] + 60000
            done.append(control["time"])
    r = replay.Replay(game, d, ai=True)
    stats = r.run(speed=4.0, clock=lambda: now[0], sleep=sleep, log=None, poll=poll, finish=True)
    assert done and stats["events"] > 0 and not any("None" in c for c in game.sent)
