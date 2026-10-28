"""#2822 (epic #2538): the trigger effect "Mirror Diplomacy" gives the source player the stances of the target player
toward each other player in the scenario mode. The converter sets the score #m<N>.p<M> of aoe_dip."""
from collections import Counter

import numpy as np
from test_scenario_diplomacy import Game

import aoe2mc
import gather
import scenario


def mirror(a=1, b=2):
    e = dict(type=aoe2mc.MIRROR_DIPLOMACY, message="", player=a, target=b, time=0, object=None, tile=[-1, -1],
             area=[-1, -1, -1, -1])
    return dict(id=7, name="Mirror", enabled=True, looping=False,
                conditions=[dict(type=aoe2mc.TIMER, timer=60, inverted=False)], effects=[e])


def test_the_trigger_function_sets_the_mirror_score():
    stats = Counter()
    load, files = aoe2mc.trigger_files([mirror()], 4, np.full((16, 16), 64, np.int16), {}, stats)
    assert files["data/aoe2mc/function/trigger/7.mcfunction"].splitlines() == [
        "scoreboard players set #m1.p2 aoe_dip 1", "scoreboard players set #any aoe_dip 1"]
    assert load[0] == "scoreboard objectives add aoe_dip dummy"
    assert stats == Counter({"mirror diplomacy": 1})


def test_gaia_or_the_same_player_makes_no_function():
    load, files = aoe2mc.trigger_files([mirror(1, 0), mirror(2, 2)], 4, np.full((16, 16), 64, np.int16), {})
    assert not files and "scoreboard objectives add aoe_dip dummy" not in load


def test_player_1_takes_the_stances_of_player_2_toward_3_and_4():
    # player 1 is an ally of 4 and an enemy of 3; player 2 is an ally of 3 and neutral to 4
    g = Game({"0": {}, "1": {"team": 1}, "2": {"team": 2, "neutral": [4]}, "3": {"team": 2}, "4": {"team": 1}},
             {"#any": 1, "#m1.p2": 1})
    scenario.diplomacy(g)
    assert gather.allied(g.players, 1, 3) and not gather.allied(g.players, 1, 4)
    assert g.players["1"].get("neutral") == [4]
    assert gather.allied(g.players, 1, 2)                            # an alliance is a team: 1 joins the team of 2 and 3
    assert g.players["2"] == {"team": 2, "neutral": [4]}             # the target keeps its stances
    assert g.scores == {}


def test_an_enemy_of_the_target_becomes_an_enemy():
    g = Game({"0": {}, "1": {"team": 1}, "2": {}, "3": {"team": 1}, "4": {}}, {"#any": 1, "#m1.p2": 1})
    scenario.diplomacy(g)
    assert not any(gather.allied(g.players, 1, k) for k in (2, 3, 4)) and "neutral" not in g.players["1"]
