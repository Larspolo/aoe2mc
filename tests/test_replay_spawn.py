"""Live replay: a trained unit appears in front of its building when its training ends (#408). Fake RCON."""
import os
import re
import sys

import pytest

import aoe2mc
from buildings import footprint

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

REC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "de-64.3.aoe2record")
TC = {"kind": "building", "name": "TOWN_CENTER", "player": 1, "ref": 5, "tile": [4.0, 4.0], "footprint": [8, 8, 24, 24]}


def queue(t=1000, amount=1, objects=(5,), name="VILLAGER_MALE", type=83, **kw):
    return dict(time=t, player=1, kind="queue", objects=list(objects), type=type, name=name, amount=amount, **kw)


def summons(cmds):
    """(entity, x, y, z) of the summon commands of units (not the production texts, #2811)."""
    out = []
    for c in cmds:
        m = re.match(r"summon (?!text_display)(\S+) (\S+) (\S+) (\S+) ", c)
        if m:
            out.append((m[1], float(m[2]), float(m[3]), float(m[4])))
    return out


def test_a_queue_of_two_gives_two_units_one_after_the_other():
    d = data([queue(amount=2)])
    d["objects"].append(TC)
    now, game = [0.0], Fake()

    def sleep(s):
        now[0] += s
    replay.Replay(game, d).run(clock=lambda: now[0], sleep=sleep, log=None, finish=True)
    assert now[0] == pytest.approx(51)                                # 1 s + 2 × 25 s of training
    (k1, x1, y1, z1), (k2, x2, y2, z2) = summons(game.sent)
    assert k1 == k2 == "minecraft:villager" and y1 == y2 == 70
    assert z1 == z2 == 24.5 and (x1, z1) != (x2, z2) and 8 <= x1 < 24     # in front of the town center (south side)
    first = next(c for c in game.sent if replay.PANEL not in c)                # not the production text (#2811)
    assert "Villager" in first and "aoe2mc.p1" in first                       # name and team tag


def test_research_delays_the_next_unit():
    tl = [queue(t=0), dict(time=1000, player=1, kind="research", objects=[5], technology="Loom"), queue(t=2000)]
    ends = [e["time"] for e in replay.Replay(Fake(), data(tl)).spawns()]
    assert ends == [25000, 75000]                                     # 25 s, Loom 25 s, 25 s


def test_a_new_building_trains_at_its_place():
    tl = [dict(time=0, player=1, kind="build", type=12, name="BARRACKS", tile=[10.5, 10.5]),
          queue(t=5000, objects=[900], name="MILITIA", type=74, names=["BARRACKS"])]
    d = data(tl)
    d["objects"].append(TC)
    r = replay.Replay(Fake(), d)
    r.commands(tl[0])
    e, = r.spawns()
    (_, rx0, rx1, rz0, rz1), = [(p, *rect) for p, n, rect in r.placed]
    (kind, x, _, z), = summons(r.commands(e))
    assert e["time"] == 26000 and rx0 <= x < rx1 and z == rz1 + 0.5


def test_no_unit_without_a_building_or_space():
    r = replay.Replay(Fake(), data([queue()]))                        # no building of player 1
    e, = r.spawns()
    assert r.commands(e) == []


def test_sample_record_villagers_per_town_center():
    """The villagers of the first 3 minutes of samples/: 7 at the town center of player 1, 6 at that of player 2."""
    pytest.importorskip("mgz.model")
    rec, timeline = aoe2mc.read_record(REC), aoe2mc.read_timeline(REC)
    size, objects = rec[0], rec[5]
    aoe2mc.name_timeline(objects, timeline)
    T, n = 4, size * 4
    d = data(timeline, n=n, y=64)
    for o in objects:
        if o["kind"] == "B":
            s = footprint(o["name"])
            x0, z0 = int(o["x"] - s / 2) * T, int(o["y"] - s / 2) * T
            d["objects"].append({"kind": "building", "name": o["name"], "player": o["player"], "ref": o["ref"],
                                 "footprint": [x0, z0, x0 + s * T, z0 + s * T]})
    r = replay.Replay(Fake(), d)
    count = {}
    for e in sorted(r.spawns(), key=lambda e: e["time"]):
        if e["time"] < 180000:
            (kind, x, _, z), = summons(r.commands(e))
            tc = next(o for o in d["objects"] if o.get("ref") == e["building"])
            x0, z0, x1, z1 = tc["footprint"]
            assert kind == "minecraft:villager" and x0 - 1 <= x <= x1 + 1 and z0 - 1 <= z <= z1 + 1
            count[tc["player"]] = count.get(tc["player"], 0) + 1
    assert count == {1: 7, 2: 6}
