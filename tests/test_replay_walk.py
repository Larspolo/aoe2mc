"""Live replay: the units of MOVE and ORDER walk on a path to the target, at their walk speed (#409). Fake RCON."""
import math
import os
import re
import sys
import time

import pytest

import aoe2mc

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_spawn import TC, queue  # noqa: E402

VIL = {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "u1", "ref": 7, "tile": [2.5, 10.5]}
HOUSE = {"kind": "building", "name": "HOUSE", "player": 1, "ref": 9, "tile": [6.0, 10.0], "footprint": [20, 36, 28, 48]}


def play(timeline, objects=(VIL, HOUSE), n=64, water=()):
    d = data(timeline, n=n)
    d["ground"] = [" ".join("-" if (x, z) in water else "70" for x in range(n)) for z in range(n)]
    d["players"]["2"]["arch"] = "mesoamerican"
    d["objects"] += list(objects)
    now, game = [0.0], Fake()

    def sleep(s):
        now[0] += s
    r = replay.Replay(game, d)
    r.run(clock=lambda: now[0], sleep=sleep, log=None, finish=True)
    return r, game.sent, now[0]


def tps(sent, uuid="u1"):
    return [(math.floor(float(m[1])), math.floor(float(m[3]))) for c in sent
            if (m := re.match(rf"tp {uuid} (\S+) (\S+) (\S+) ", c))]


def test_a_move_walks_on_a_free_path_at_the_walk_speed():
    r, sent, end = play([dict(time=1000, player=1, kind="move", objects=[7], tile=[10.5, 10.5], names=["VILLAGER_MALE"])])
    cells = tps(sent)
    assert cells[-1] == (42, 42)                                       # the target tile
    house = {(x, z) for x in range(20, 28) for z in range(36, 48)}
    assert not set(cells) & house and all(r.map.free(*c) for c in cells)
    steps = [math.dist(a, b) for a, b in zip([(10, 42)] + cells, cells)]
    assert all(s <= 1.5 for s in steps)
    assert end == pytest.approx(1 + sum(steps) / (0.8 * 4), abs=0.2)   # 0.8 tiles per second
    assert r.units[7].pos[0] == 42.5 and not r.moving


def test_an_order_walks_next_to_its_target():
    r, sent, _ = play([dict(time=0, player=1, kind="order", objects=[7], target=9, tile=[6.0, 10.0])])
    x, z = tps(sent)[-1]
    assert 19 <= x <= 28 and 35 <= z <= 48 and not (20 <= x < 28 and 36 <= z < 48)


def test_a_new_id_takes_the_spawned_unit():
    tl = [queue(t=0), dict(time=30000, player=1, kind="move", objects=[500], tile=[1.5, 7.5], names=["VILLAGER_MALE"])]
    r, sent, _ = play(tl, [TC])
    uuid = re.search(r"UUID:\[I;([-\d,]+)\]", next(c for c in sent if c.startswith("summon")))[1]
    v = r.units[500]
    assert v.uuid == replay.units.uuid_str([int(n) for n in uuid.split(",")])
    assert tps(sent, v.uuid)[-1] == (6, 30)


def test_an_unknown_unit_or_target_does_not_move():
    r, sent, _ = play([dict(time=0, player=1, kind="move", objects=[99], tile=[3.5, 3.5], names=[None]),
                       dict(time=0, player=1, kind="order", objects=[7], target=12345)])
    assert not tps(sent) and not r.moving


def test_sample_record_moves():
    """The first minute of samples/: the units walk, and the paths take little time."""
    pytest.importorskip("mgz.model")
    rec = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "de-64.3.aoe2record")
    size, objects, timeline = *aoe2mc.read_record(rec)[0:6:5], aoe2mc.read_timeline(rec)
    aoe2mc.name_timeline(objects, timeline)
    objs = []
    for o in objects:
        if o["kind"] == "U" and o.get("ref") is not None:
            objs.append({"kind": "unit", "name": o["name"], "player": o["player"], "uuid": f"u{o['ref']}",
                         "ref": o["ref"], "tile": [o["x"], o["y"]]})
    t = time.perf_counter()
    r, sent, _ = play([e for e in timeline if e["time"] < 60000], objs, n=size * 4)
    assert time.perf_counter() - t < 10
    walkers = {c.split()[1] for c in sent if c.startswith("tp ")}
    assert len(walkers) >= 8


def test_a_new_command_without_a_path_stops_the_unit():
    ring = {(50 + dx, 50 + dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1)} - {(50, 50)}
    r, sent, _ = play([dict(time=0, player=1, kind="move", objects=[7], tile=[10.5, 10.5]),
                       dict(time=2000, player=1, kind="move", objects=[7], tile=[12.5, 12.5])], water=ring)  # an island
    assert not r.moving and len(tps(sent)) == len([c for c in sent if c.startswith("tp ")]) > 0


def test_a_new_building_pushes_the_units_out():
    for tl in ([dict(time=0, player=1, kind="move", objects=[7], tile=[0.5, 0.5])], []):    # walking and standing
        tl.append(dict(time=500, player=1, kind="build", type=70, name="HOUSE", tile=[3.0, 11.0]))   # 8..15, 40..47
        r, sent, _ = play(tl)
        v = r.units[7]
        assert not (8 <= v.pos[0] < 16 and 40 <= v.pos[2] < 48) and r.map.free(*v.cell)


def test_a_new_building_on_the_way_gives_a_new_path():
    tl = [dict(time=0, player=1, kind="move", objects=[7], tile=[14.5, 10.5]),
          dict(time=500, player=1, kind="build", type=70, name="HOUSE", tile=[10.0, 11.0])]   # blocks 36..43, 40..47
    r, sent, _ = play(tl)
    cells = tps(sent)
    assert cells[-1] == (58, 42) and all(r.map.free(*c) for c in cells[3:])
