"""A trigger with the condition "Object Attacked" fires in the converted world when its unit takes damage (#2779): the
tick function tests the HurtTime of the unit with the tag aoe2mc.r<ref> (#2617), 10 ticks after each hit."""

import aoe2mc
import triggers

CHAT = dict(type=aoe2mc.SEND_CHAT, message="We are attacked.", player=1, time=0, object=None, tile=[-1, -1],
            area=[-1] * 4)


def attacked(ref=5, unit=True):
    return dict(type=aoe2mc.OBJECT_ATTACKED, timer=0, inverted=False, ref=ref, unit=unit, player=2)


def files(conds, stats=None):
    trig = dict(id=3, name="t", enabled=True, looping=False, conditions=conds, effects=[CHAT])
    return aoe2mc.trigger_files([trig], stats=stats)[1]


def test_the_tick_function_tests_the_hurt_time_of_the_unit():
    assert files([attacked()])["data/aoe2mc/function/tick.mcfunction"].splitlines() == [
        "execute if entity @e[tag=aoe2mc.r5,predicate=aoe2mc:attacked] unless score #3 aoe_trig matches 1 "
        "run function aoe2mc:trigger/3"]


def test_a_building_tests_the_score_of_its_hits_not_the_tag():
    assert "execute if score #h5 aoe_hit matches 1 unless score #3 aoe_trig matches 1 run function aoe2mc:trigger/3" \
        in files([attacked(unit=False)])["data/aoe2mc/function/tick.mcfunction"]


def test_read_scenario_keeps_the_object_and_the_map_names_the_command():
    assert aoe2mc.OBJECT_ATTACKED in aoe2mc.OBJECT_TESTS           # read_scenario adds ref, unit and player
    assert "HurtTime" in triggers.MAP[("condition", "OBJECT_ATTACKED")]
    assert "#2779" in triggers.MAP[("condition", "OBJECT_ATTACKED")]


def test_the_predicate_accepts_the_hurt_time_or_the_hit_tag_of_the_plugin():      # #3085
    pred = files([attacked()])["data/aoe2mc/predicate/attacked.json"]
    assert pred == aoe2mc.attacked_predicate() and pred["type"] == "minecraft:any_of"
    assert [t.get("term", t)["predicate"]["minecraft:nbt"] for t in pred["terms"]] == ["{HurtTime:0s}", '{Tags:["aoe2mc.hit"]}']
