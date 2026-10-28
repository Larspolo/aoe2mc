"""#2655 (epic #2538): a trigger with the condition "Accumulate Attribute" fires on a resource score of the game
program (the sidebar scores of Gather.board)."""
import numpy as np

import aoe2mc


def trigger(player=2, attribute=3, quantity=100):
    c = dict(type=aoe2mc.ACCUMULATE_ATTRIBUTE, timer=-1, inverted=False, quantity=quantity, player=player,
             attribute=attribute)
    e = dict(type=aoe2mc.SEND_CHAT, message="Rich", player=1, time=0)
    return dict(id=7, name="Rich", enabled=True, looping=False, conditions=[c], effects=[e])


def files(*triggers):
    return aoe2mc.trigger_files(list(triggers), 4, np.full((16, 16), 64, np.int16), {})[1]


def test_the_tick_function_tests_the_gold_of_player_2():
    tick = files(trigger())["data/aoe2mc/function/tick.mcfunction"]
    assert "execute if score Gold aoe_res2 matches 100.. unless score #7 aoe_trig matches 1 run function " \
           "aoe2mc:trigger/7" in tick


def test_player_1_has_the_board_without_a_number():
    assert "if score Food aoe_res matches 50.." in files(trigger(1, 0, 50))["data/aoe2mc/function/tick.mcfunction"]


def test_an_attribute_that_is_no_resource_makes_no_function():
    assert files(trigger(attribute=4)) == {}
