"""#2768 (epic #2538): the trigger effect "Modify Resource by Variable" adds, subtracts or sets the score #p<N>.<resource>
from the score #v<N> of aoe_var (aoe2mc.resource_by_variable_lines), and scenario.resources puts it into the stock."""
import os
import sys

from AoE2ScenarioParser.datasets.trigger_lists import Operation

import aoe2mc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import scenario  # noqa: E402
from test_scenario_mode import game  # noqa: E402
from test_scenario_resources import Scores, lines  # noqa: E402


def effect(op, player=1, resource=3, variable=3):
    return lines(dict(type=aoe2mc.MODIFY_RESOURCE_BY_VARIABLE, player=player, resource=resource, operation=op,
                      variable=variable))


def test_add_of_variable_3_to_the_gold_of_player_1_finds_the_operation_line():
    load, fn = effect(Operation.ADD)
    assert fn == ["scoreboard players operation #p1.gold aoe_res += #v3 aoe_var"]
    assert "scoreboard objectives add aoe_res dummy" in load


def test_subtract_takes_the_variable_from_the_stock_change():
    assert effect(Operation.SUBTRACT)[1] == ["scoreboard players operation #p1.gold aoe_res -= #v3 aoe_var"]


def test_set_copies_the_variable_to_aoe_set_and_drops_the_earlier_changes():
    assert effect(Operation.SET)[1] == ["scoreboard players operation #p1.gold aoe_set = #v3 aoe_var",
                                        "scoreboard players reset #p1.gold aoe_res"]


def test_gaia_and_a_missing_variable_write_no_line():   # multiply and divide: #2941
    assert effect(Operation.ADD, player=0)[1] == []
    assert effect(Operation.ADD, variable=-1)[1] == []


def test_resources_puts_the_variable_value_into_the_gold_of_player_1():
    server, g, bot = game({"1": {}, "2": {}})
    g.stock.update(gold=300)
    Scores(server, {("#p1.gold", "aoe_res"): 40})          # the result of "+= #v3 aoe_var" with the variable at 40
    scenario.resources(g)
    assert g.stock["gold"] == 340 and f"scoreboard players set Gold {g.board} 340" in server.log
