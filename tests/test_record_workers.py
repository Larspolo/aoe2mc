"""Record IDs (#765): an ID that builds or gathers on land is a villager, not a ship or a soldier."""
import os

import pytest

import aoe2mc

REC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "de-64.3.aoe2record")


def obj(ref, name, player=1):
    return dict(kind="B" if name in ("TOWN_CENTER", "DOCK") else "U", name=name, player=player, x=0, y=0, ref=ref)


def test_a_building_unit_is_a_villager():
    objects = [obj(5, "TOWN_CENTER"), obj(6, "DOCK"), obj(8, "TREE_OAK", 0)]
    timeline = [dict(time=0, player=1, kind="queue", objects=[6], name="FISHING_SHIP", amount=1),     # done at 40 s
                dict(time=20000, player=1, kind="queue", objects=[5], name="VILLAGER_MALE", amount=1),  # done at 45 s
                dict(time=60000, player=1, kind="build", objects=[13], name="HOUSE", tile=[3.0, 4.0])]
    names = aoe2mc.name_timeline(objects, timeline)
    assert names[13] == "VILLAGER_MALE" and timeline[2]["names"] == ["VILLAGER_MALE"]
    assert "FISHING_SHIP" in names.values()


def test_a_unit_that_chops_a_tree_is_a_villager():
    objects = [obj(5, "TOWN_CENTER"), obj(6, "DOCK"), obj(8, "TREE_OAK", 0)]
    timeline = [dict(time=0, player=1, kind="queue", objects=[6], name="FISHING_SHIP", amount=1),
                dict(time=20000, player=1, kind="queue", objects=[5], name="VILLAGER_MALE", amount=1),
                dict(time=60000, player=1, kind="order", objects=[13], target=8)]
    assert aoe2mc.name_timeline(objects, timeline)[13] == "VILLAGER_MALE"


def test_sample_record_has_no_ship_or_soldier_that_builds():
    pytest.importorskip("mgz.model")
    objects, timeline = aoe2mc.read_record(REC)[5], aoe2mc.read_timeline(REC)
    aoe2mc.name_timeline(objects, timeline)
    builders = {n for e in timeline if e["kind"] in ("build", "wall") for n in e["names"] if n}
    assert builders and all("VILLAGER" in n for n in builders), builders       # 32 soldiers and ships before #765
