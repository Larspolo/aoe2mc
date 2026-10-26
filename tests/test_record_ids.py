"""The object IDs of a recorded game (#407): start objects keep their ID, new objects get the next free ID."""
import os

import pytest

import aoe2mc

REC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "de-64.3.aoe2record")


def obj(ref, name, player=1):
    return dict(kind="B" if name == "TOWN_CENTER" else "U", name=name, player=player, x=0, y=0, ref=ref)


def test_new_ids_in_the_order_that_the_game_makes_objects():
    objects = [obj(5, "TOWN_CENTER"), obj(10, "VILLAGER_MALE")]
    timeline = [dict(time=1000, player=1, kind="build", objects=[10], name="HOUSE", tile=[3.0, 4.0]),
                dict(time=2000, player=1, kind="queue", objects=[5], name="VILLAGER_MALE", amount=2),
                dict(time=30000, player=1, kind="move", objects=[13, 10], tile=[1.0, 1.0]),   # 12: not in the record
                dict(time=60000, player=1, kind="order", objects=[14], target=11)]
    names = aoe2mc.name_timeline(objects, timeline)
    assert names[11] == "HOUSE" and names[13] == names[14] == "VILLAGER_MALE" and 12 not in names
    assert timeline[2]["names"] == ["VILLAGER_MALE", "VILLAGER_MALE"] and timeline[1]["names"] == ["TOWN_CENTER"]


def test_an_id_in_use_before_the_command_is_older():
    objects = [obj(5, "TOWN_CENTER")]
    timeline = [dict(time=1000, player=1, kind="move", objects=[30], tile=[1.0, 1.0]),    # made before: not ours
                dict(time=2000, player=1, kind="queue", objects=[5], name="VILLAGER_MALE", amount=1),
                dict(time=40000, player=1, kind="move", objects=[31], tile=[1.0, 1.0])]
    assert aoe2mc.name_timeline(objects, timeline) == {5: "TOWN_CENTER", 31: "VILLAGER_MALE"}


def test_a_building_is_named_by_its_units():
    objects = [obj(5, "TOWN_CENTER")]
    timeline = [dict(time=1000, player=1, kind="queue", objects=[40], name="SPEARMAN", amount=1)]
    assert aoe2mc.name_timeline(objects, timeline)[40] == "BARRACKS"


def test_sample_record():
    pytest.importorskip("mgz.model")
    objects, timeline = aoe2mc.read_record(REC)[5], aoe2mc.read_timeline(REC)
    names = aoe2mc.name_timeline(objects, timeline)
    early = {i: n for e in timeline if e["time"] < 300000 and e["player"] == 1 and e["kind"] in aoe2mc.UNIT_USE
             for i, n in zip(e.get("objects", ()), e["names"])}
    assert len(early) >= 30 and sum(n is not None for n in early.values()) >= 0.9 * len(early)
    assert names[9918] == names[9919] == "VILLAGER_MALE" and names[9933] == "LUMBER_CAMP" and names[1646] == "TOWN_CENTER"
    for e in timeline:                      # each training building has the name of the building of its units
        if e["kind"] == "queue" and aoe2mc.train(e["name"]):
            assert set(e["names"]) <= {aoe2mc.train(e["name"])[1], None}, e
