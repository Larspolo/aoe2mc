"""Live replay: an ORDER or a GARRISON command on an own town center puts the units inside it, UNGARRISON lets them out
(#809). Fake RCON."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

import aoe2mc  # noqa: E402

TC = {"kind": "building", "name": "TOWN_CENTER", "player": 1, "ref": 50, "tile": [8.0, 8.0],
      "footprint": [24, 24, 40, 40], "inside": {"y": 71, "cells": [[30, 30], [33, 30]]}}
RECT = (24, 40, 24, 40)
TREE = {"kind": "other", "name": "TREE_OAK", "player": 0, "ref": 20, "tile": [3.5, 12.5]}


def vil(ref, uuid, tile):
    return {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": uuid, "ref": ref, "tile": tile}


def order(t, refs, target, kind="order"):
    return dict(time=t, player=1, kind=kind, objects=refs, target=target, names=["VILLAGER_MALE"] * len(refs))


def ungarrison(t):
    return dict(time=t, player=1, kind="ungarrison", objects=[50])


def play(timeline, end, ai=False, extra=()):
    d = data(timeline + [dict(time=end, player=1, kind="chat", text="end")])
    d["objects"] += [TC, vil(7, "u1", [2.5, 10.5]), vil(8, "u2", [2.5, 11.5]), *extra]
    now, game = [0.0], Fake()

    def sleep(s):
        now[0] += s
    r = replay.Replay(game, d, ai=ai)
    r.run(clock=lambda: now[0], sleep=sleep, log=None)
    return r, game.sent


@pytest.mark.parametrize("ai", [False, True])
@pytest.mark.parametrize("kind", ["order", "garrison"])
def test_two_villagers_go_into_their_town_center_after_the_walk(ai, kind):
    r, sent = play([order(0, [7, 8], 50, kind)], 30000, ai)
    assert r.garrisons == {RECT: [7, 8]} and not r.entering
    assert "tp u1 30.5 71 30.5" in sent and "tp u2 33.5 71 30.5" in sent
    assert "tag u1 add aoe2mc.garrisoned" in sent and "data merge entity u2 {Invulnerable:1b,NoAI:1b,CustomNameVisible:0b}" in sent
    assert ("aoe stop u1" in sent) == ai
    k = sent.index("tag u1 add aoe2mc.garrisoned")
    assert any(c.startswith(("tp u1", "aoe moveto u1")) for c in sent[:k - 2])   # it walked there first


@pytest.mark.parametrize("ai", [False, True])
def test_ungarrison_puts_them_out_next_to_the_building(ai):
    r, sent = play([order(0, [7, 8], 50), ungarrison(20000)], 30000, ai)
    assert r.garrisons == {}
    assert "tag u1 remove aoe2mc.garrisoned" in sent and "data merge entity u2 {Invulnerable:0b}" in sent
    out = [c for c in sent if c.startswith("tp u") and sent.index(c) > sent.index("tag u2 add aoe2mc.garrisoned")]
    for c in out:
        x, _, z = map(float, c.split()[2:])
        assert (23 <= x <= 40 and z in (40.5, 23.5)) or (x in (23.5, 40.5) and 23 <= z <= 40)   # next to it
    assert ("aoe label u1" in sent) == ai


def test_a_move_takes_a_unit_out():
    """AoE2 selects no unit inside a building: a MOVE in the record says that the unit is out (#1229)."""
    tl = [order(0, [7], 50), dict(time=15000, player=1, kind="move", objects=[7], tile=[1.5, 1.5], names=["VILLAGER_MALE"])]
    r, sent = play(tl, 30000)
    x, z = r.units[7].cell                                             # the tile 1.5 1.5: cells 4 to 7
    assert r.garrisons == {} and 4 <= x < 8 and 4 <= z < 8 and "tag u1 remove aoe2mc.garrisoned" in sent


def test_a_villager_with_wood_drops_it_and_stays_out():
    tl = [order(0, [7], 20), order(30000, [7], 50)]
    r, sent = play(tl, 60000, extra=[TREE])
    assert r.units[7].load > 0 and r.garrisons == {} and not r.entering
    assert not any("aoe2mc.garrisoned" in c for c in sent)
    r, sent = play(tl[:1] + [order(30000, [7], 50, "garrison")], 60000, extra=[TREE])
    assert r.garrisons == {RECT: [7]}                                  # the garrison command takes it in


def test_jump_puts_them_inside():
    d = data([order(0, [7, 8], 50)])
    d["objects"] += [TC, vil(7, "u1", [2.5, 10.5]), vil(8, "u2", [2.5, 11.5])]
    r = replay.Replay(Fake(), d)
    sent = r.jump(d["timeline"], 10000)
    assert r.garrisons == {RECT: [7, 8]} and "tag u2 add aoe2mc.garrisoned" in sent


@pytest.mark.slow
def test_the_sample_record_has_garrison_commands():
    tl = aoe2mc.read_timeline(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                           "samples", "de-64.3.aoe2record"))
    g = [e for e in tl if e["kind"] == "garrison"]
    assert len(g) == 20 and len([e for e in tl if e["kind"] == "ungarrison"]) == 8
    assert g[0]["objects"] == [1662] and g[0]["target"] == 1652
