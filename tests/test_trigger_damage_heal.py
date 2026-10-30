"""A negative amount of the trigger effect "Damage Object" heals the units of its player in its area, as in AoE2
(#2907): the same commands as "Heal Object" (#2692) with the amount turned positive."""
from collections import Counter

import test_trigger_damage as damage
import test_trigger_heal as heal

import aoe2mc


def test_a_negative_damage_gives_the_commands_of_heal_object():
    stats = Counter()
    found = damage.lines([damage.effect(-20)], stats)
    assert found == heal.lines([heal.effect(20)])[1] and len(found) == 10
    assert found[2].endswith(" run scoreboard players add @s aoe_hp 20") and stats == Counter(damage=1)


def test_a_negative_damage_makes_the_scores_of_the_heal():
    t = dict(id=7, name="t", enabled=True, looping=False,
             conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)], effects=[damage.effect(-5, "MILITIA")])
    load = aoe2mc.trigger_files([t], 4, damage.np.full((64, 64), 70, damage.np.int16), {1: {"color": "blue"}},
                                Counter())[0]
    assert any("scoreboard objectives add aoe_hp dummy" in line for line in load)


def test_a_positive_damage_still_damages():
    assert damage.lines([damage.effect(20)])[0].endswith(" run damage @s 20")


def test_a_negative_damage_of_a_building_is_an_order_of_the_game_program():   # #3776
    stats = Counter()
    e = damage.effect(-10) | {"object": ("B", "CASTLE")}
    assert damage.lines([e], stats) == ['data modify storage aoe2mc:orders list append value "damage 1 CASTLE 2 3 4 5 -10"']
    assert stats == Counter({"damage (building)": 1})
