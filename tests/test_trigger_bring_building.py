"""The conditions "Bring Object to Area" and "Bring Object to Object" with a building (#3782): a building does not move,
so the converter knows its tile; the test is its aoe_fallen score (#2910) or the other unit near its tile."""
import aoe2mc

CHAT = dict(type=aoe2mc.SEND_CHAT, message="Here.", player=1, time=0, object=None, tile=[-1, -1], area=[-1] * 4)


def tick(c):
    t = dict(id=3, name="t", enabled=True, looping=False, conditions=[c], effects=[CHAT])
    return aoe2mc.trigger_files([t])[1].get("data/aoe2mc/function/tick.mcfunction", "").splitlines()


def area(tile, inverted=False):
    return dict(type=aoe2mc.BRING_OBJECT_TO_AREA, timer=0, inverted=inverted, ref=7, unit=False, area=[2, 3, 1, 2],
                tile=tile)


def test_a_building_in_the_area_holds_while_it_stands():
    assert tick(area([2, 2])) == ["execute unless score #f7 aoe_fallen matches 1.. unless score #3 aoe_trig matches 1 "
                                  "run function aoe2mc:trigger/3"]
    assert aoe2mc.fallen_list([dict(id=3, name="t", enabled=True, looping=False, conditions=[area([2, 2])],
                                    effects=[CHAT])]) == [7]


def test_a_building_outside_the_area_never_holds():
    assert tick(area([9, 9])) == ["execute if score #never aoe_trig matches 1 unless score #3 aoe_trig matches 1 "
                                  "run function aoe2mc:trigger/3"]
    assert tick(area([9, 9], inverted=True))[0].startswith("execute unless score #never aoe_trig matches 1 ")


def test_bring_object_to_object_with_a_building_uses_its_tile():
    c = dict(type=aoe2mc.BRING_OBJECT_TO_OBJECT, timer=0, inverted=False, ref=5, unit=True, next=7, next_unit=False,
             tile=None, next_tile=[3, 4])
    box = f"@e[tag=aoe2mc.r5,dx=11,dy={aoe2mc.HEIGHT - 1},dz=11]"
    assert tick(c) == [f"execute unless score #f7 aoe_fallen matches 1.. positioned 8 {aoe2mc.MIN_Y} 12 if entity {box} "
                       "unless score #3 aoe_trig matches 1 run function aoe2mc:trigger/3"]
    swapped = dict(c, ref=7, unit=False, next=5, next_unit=True, tile=[3, 4], next_tile=None)
    assert tick(swapped) == tick(c)


def test_a_building_without_a_tile_gives_no_trigger():
    assert tick(area(None)) == []
