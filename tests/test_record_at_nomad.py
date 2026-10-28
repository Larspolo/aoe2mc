"""--at of a Nomad record: the units of a player with no start building (#3033)."""
import aoe2mc


def test_units_stand_at_the_first_built_building():
    objects = [dict(kind="U", name="VILLAGER_MALE", player=1, x=12.5, y=12.5, ref=6)]
    timeline = [dict(time=1000, player=1, kind="build", type=109, tile=[20.5, 20.5]),
                dict(time=200000, player=1, kind="queue", type=83, objects=[9001], amount=3)]
    objs, stats = aoe2mc.apply_timeline(objects, timeline, 600000)
    units = [o for o in objs if o["kind"] == "U" and o.get("ref") is None]
    assert [(o["name"], o["x"], o["y"]) for o in units] == [("VILLAGER_MALE", 20.5, 20.5)] * 3
    assert stats["units (QUEUE commands, at their building)"] == 3
    assert stats["units without a building (QUEUE commands)"] == 0


def test_units_without_any_building_are_counted():
    timeline = [dict(time=1000, player=1, kind="queue", type=83, objects=[5], amount=2)]
    objs, stats = aoe2mc.apply_timeline([], timeline, 600000)
    assert [o for o in objs if o["kind"] == "U"] == []
    assert stats["units without a building (QUEUE commands)"] == 2
