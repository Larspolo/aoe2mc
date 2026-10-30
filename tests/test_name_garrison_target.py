"""The target of a GARRISON command is a building or a ship: name_timeline does not give its ID a trained unit (#912)."""
import os

import pytest
from test_record_ids import REC, obj

import aoe2mc


def test_a_garrison_target_gets_the_building_name():
    objects = [obj(5, "TOWN_CENTER"), obj(10, "VILLAGER_MALE")]
    timeline = [dict(time=0, player=1, kind="queue", objects=[5], name="VILLAGER_MALE", amount=1),   # made at 25 s
                dict(time=26000, player=1, kind="build", objects=[10], name="HOUSE", tile=[3.0, 4.0]),
                dict(time=60000, player=1, kind="garrison", objects=[10], target=11),
                dict(time=70000, player=1, kind="move", objects=[12], tile=[1.0, 1.0])]
    names = aoe2mc.name_timeline(objects, timeline)
    assert names[11] == "HOUSE" and names[12] == "VILLAGER_MALE"
    assert timeline[2]["target_name"] == "HOUSE"


def test_a_ship_can_be_a_garrison_target():
    objects = [obj(5, "DOCK")]
    timeline = [dict(time=0, player=1, kind="queue", objects=[5], name="TRANSPORT_SHIP", amount=1),
                dict(time=90000, player=1, kind="garrison", objects=[3], target=6)]
    assert aoe2mc.name_timeline(objects, timeline)[6] == "TRANSPORT_SHIP"


@pytest.mark.slow
def test_no_garrison_target_of_the_sample_is_a_unit():
    pytest.importorskip("mgz.model")
    if not os.path.exists(REC):
        pytest.skip("no sample record")
    objects, timeline = aoe2mc.read_record(REC)[5], aoe2mc.read_timeline(REC)
    names = aoe2mc.name_timeline(objects, timeline)
    for i in (12251, 17797):
        assert names.get(i) is None or aoe2mc.train(names[i]) is None, (i, names[i])
