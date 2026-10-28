"""#2710 (epic #2538): a trigger with the condition "Player Defeated" fires in the scenario mode. The game program sets
the score #p<N> of aoe_lost when it defeats player N (conquest, regicide), and the tick function of the datapack tests
it."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import aoe2mc  # noqa: E402
import triggers  # noqa: E402
from test_conquest import check, live, setup  # noqa: E402


def trig(player=2):
    return dict(id=7, name="t", enabled=True, looping=False,
                conditions=[dict(type=aoe2mc.PLAYER_DEFEATED, timer=0, inverted=False, player=player)],
                effects=[dict(type=aoe2mc.SEND_CHAT, message="Won!", player=1, time=0, object=None, tile=[-1, -1],
                              area=[-1] * 4)])


def test_the_condition_tests_the_score_of_the_player_in_the_tick_function():
    load, files = aoe2mc.trigger_files([trig()])
    assert "execute if score #p2 aoe_lost matches 1.. unless score #7 aoe_trig matches 1 run function " \
           "aoe2mc:trigger/7" in files["data/aoe2mc/function/tick.mcfunction"].splitlines()
    assert "scoreboard objectives add aoe_lost dummy" in load


def test_gaia_gives_no_trigger():
    assert aoe2mc.trigger_files([trig(player=0)])[1] == {}


def test_a_defeat_of_the_scenario_mode_sets_the_score():
    server, g = setup((1, 2, 3))
    live(server, {1, 3})
    check(g)
    assert "scoreboard players set #p2 aoe_lost 1" not in server.log            # not in the other modes
    server, g = setup((1, 2, 3))
    g.mode = "scenario"
    live(server, {1, 3})
    check(g)
    assert "scoreboard players set #p2 aoe_lost 1" in server.log
    assert "scoreboard players set #p3 aoe_lost 1" not in server.log


def test_the_map_line_names_this_issue():
    assert "#2710" in triggers.MAP[("condition", "PLAYER_DEFEATED")]
