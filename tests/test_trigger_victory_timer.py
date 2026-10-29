"""#2906 (epic #2538): a trigger with the condition "Victory Timer" fires in the scenario mode of the game program.
The tick function tests the score #p<player>.<type> of aoe_vic; scenario.victory_timers sets it to the years that are
left on the wonder, relic or King of the Hill timer of the player."""
import contextlib
import io
import os
import sys
import types

import numpy as np
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import aoe2mc  # noqa: E402
import gather  # noqa: E402
import scenario  # noqa: E402
from test_gather import FakeServer, grid  # noqa: E402
from tools import scenarios  # noqa: E402

WONDER, RELIC, HILL = 0, 1, 2                                          # AoE2 VictoryTimerType
EQUAL, LESS, LARGER, LESS_OR_EQUAL = 0, 1, 2, 3                        # AoE2 Comparison


def trig(quantity=50, player=2, comparison=LESS_OR_EQUAL, kind=WONDER, inverted=False):
    c = dict(type=aoe2mc.VICTORY_TIMER, timer=0, inverted=inverted, quantity=quantity, player=player,
             comparison=comparison, timer_type=kind)
    return dict(id=3, name="t", enabled=True, looping=False, conditions=[c],
                effects=[dict(type=aoe2mc.SEND_CHAT, message="Soon", player=1, time=0, object=None, tile=[-1, -1],
                              area=[-1] * 4)])


def tick(t):
    load, out = aoe2mc.trigger_files([t], 4, np.full((16, 16), 64, np.int16))
    return load, out.get("data/aoe2mc/function/tick.mcfunction", "")


def test_the_tick_function_tests_the_years_left_on_the_timer_of_the_player():
    load, text = tick(trig())
    assert "execute if score #p2.0 aoe_vic matches ..50 unless score #3 aoe_trig matches 1 run function " \
           "aoe2mc:trigger/3" in text
    assert "scoreboard objectives add aoe_vic dummy" in load
    assert "score #p1.1 aoe_vic matches 11.." in tick(trig(quantity=10, player=1, comparison=LARGER, kind=RELIC))[1]


def test_gaia_an_unknown_timer_or_comparison_writes_no_trigger():
    for t in (trig(player=0), trig(kind=3), trig(comparison=9)):
        assert tick(t)[1] == ""


def test_the_converter_reads_the_condition_of_a_scenario(tmp_path):
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(scenarios.tiny(str(tmp_path / "tiny.aoe2scenario")))
    t = scn.trigger_manager.add_trigger("Wonder soon")
    t.new_condition.victory_timer(quantity=20, source_player=2, comparison=LESS, victory_timer_type=RELIC)
    t.new_effect.send_chat(source_player=1, message="Soon.")
    path = scenarios.save(scn, str(tmp_path / "a.aoe2scenario"))
    (got,) = aoe2mc.read_scenario(path)[4]["triggers"]
    c = got["conditions"][0]
    assert (c["type"], c["quantity"], c["player"], c["comparison"], c["timer_type"]) == \
        (aoe2mc.VICTORY_TIMER, 20, 2, LESS, RELIC)
    assert "execute if score #p2.1 aoe_vic matches ..19 " in tick(got)[1]


def game():
    server = FakeServer({})
    data = grid([[64] * 12 for _ in range(12)], [])
    data["players"] = {"0": {}, "1": {}, "2": {}}
    g = gather.Gather(server, data)
    g.bots = [types.SimpleNamespace(g=gather.Gather(server, data, player=2))]
    return server, g


def test_the_scenario_mode_sets_the_years_of_each_running_timer():
    server, g = game()
    g.wonders = {"w1": {"player": 2, "left": 1000.0}, "w2": {"player": 2, "left": 401.0}}   # the lower one: 81 years
    g.relic_timer = {"player": 1, "left": 25.0, "shown": None}
    g.hill = {"owner": None, "left": 500.0}                            # nobody holds the monument: no timer
    scenario.victory_timers(g)
    assert [c for c in server.log if " aoe_vic " in c] == ["scoreboard players set #p1.1 aoe_vic 5",
                                                           "scoreboard players set #p2.0 aoe_vic 81"]


def test_a_change_sends_one_command_and_a_stopped_timer_resets_its_score():
    server, g = game()
    g.hill = {"owner": 1, "left": 50.0}
    scenario.victory_timers(g)
    n = len(server.log)
    g.hill["left"] = 44.0
    scenario.victory_timers(g)
    assert len(server.log) == n                                        # in the same second
    g.victory_timer_at = 0.0
    scenario.victory_timers(g)
    assert server.log[n:] == ["scoreboard players set #p1.2 aoe_vic 9"]
    g.hill["owner"], g.victory_timer_at = None, 0.0
    scenario.victory_timers(g)
    assert server.log[-1] == "scoreboard players reset #p1.2 aoe_vic"

