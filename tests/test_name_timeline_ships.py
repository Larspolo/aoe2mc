"""#2629: a recorded unit whose first MOVE goes inland is not named as a ship; it gets the last land unit of its
player (aoe2mc.name_timeline with the water tiles)."""
import os

import numpy as np

import aoe2mc

REC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "de-64.3.aoe2record")
WATER = np.zeros((40, 40), bool)
WATER[:, :10] = True                                     # a lake at y < 10, land from y = 10


def obj(ref, name, player=1):
    return dict(kind="B", name=name, player=player, x=0, y=0, ref=ref)


def timeline(tile):
    return [dict(time=1000, player=1, kind="queue", objects=[5], name="FISHING_SHIP", amount=1),
            dict(time=60000, player=1, kind="queue", objects=[6], name="SPEARMAN", amount=1),   # after the ship
            dict(time=200000, player=1, kind="move", objects=[11], tile=tile)]


def test_a_unit_that_walks_inland_is_not_a_ship():
    objects = [obj(5, "DOCK"), obj(6, "BARRACKS")]
    assert aoe2mc.name_timeline(objects, timeline([20.0, 30.0]), water=WATER)[11] == "SPEARMAN"
    assert aoe2mc.name_timeline(objects, timeline([20.0, 11.0]), water=WATER)[11] == "FISHING_SHIP"   # the shore
    assert aoe2mc.name_timeline(objects, timeline([20.0, 30.0]))[11] == "FISHING_SHIP"   # no water map: as before


def test_a_worker_inland_gets_the_villager():
    objects = [obj(5, "DOCK"), obj(6, "BARRACKS"), obj(7, "TOWN_CENTER")]
    events = timeline([20.0, 30.0])[:2] + [
        dict(time=3000, player=1, kind="queue", objects=[7], name="VILLAGER_MALE", amount=1),
        dict(time=200000, player=1, kind="move", objects=[11], tile=[20.0, 30.0]),
        dict(time=201000, player=1, kind="build", objects=[11], name="HOUSE", tile=[20.0, 30.0])]
    assert aoe2mc.name_timeline(objects, events, water=WATER)[11] == "VILLAGER_MALE"


def test_unit_10047_of_the_sample_record_is_a_land_soldier():
    size, terrain, elevation, tnames, texts, objects, players = aoe2mc.read_map(REC, 1)
    water = np.vectorize(lambda t: aoe2mc.terrain_style(tnames.get(int(t), "GRASS_1"))["depth"] > 0, otypes=[bool])(terrain)
    names = aoe2mc.name_timeline(objects, aoe2mc.read_timeline(REC), water=water)
    assert names[10047] == "SPEARMAN" and aoe2mc.train(names[10047])[1] != "DOCK"
