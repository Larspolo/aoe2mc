"""#2819 (epic #2538): the trigger effect "Change Technology Cost" puts the new cost of a technology of a player into
the data storage aoe2mc:costs (the text of "Change Object Cost", #2776); the scenario mode of the game program uses
it in the menu. The other players keep the old cost."""
import contextlib
import io

import numpy as np
from AoE2ScenarioParser.datasets.techs import TechInfo
from test_civ_costs import setup
from test_scenario_patrol import trigger
from test_trigger_cost import GOLD, WOOD, costs

import aoe2mc
from game import train  # noqa: E402
from tools import scenarios  # noqa: E402


def lines(cost, technology="LOOM"):
    t = trigger(aoe2mc.CHANGE_TECHNOLOGY_COST)
    t["effects"][0].update(technology=technology, cost=cost)
    return aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16))[1].get(
        "data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_the_trigger_function_stores_the_new_cost_of_the_technology():
    assert lines([[GOLD, 100], [WOOD, 0], [-1, 0]]) == [
        'data modify storage aoe2mc:costs list append value "1 LOOM gold=100"']


def test_a_converted_trigger_stores_the_cost_of_loom(tmp_path):
    scn = scenarios.new_scenario(16)
    t = scn.trigger_manager.add_trigger("Cheap loom")
    t.new_condition.timer(timer=1)
    t.new_effect.change_technology_cost(source_player=1, technology=TechInfo.LOOM.ID, resource_1=GOLD,
                                        resource_1_quantity=100, resource_2=WOOD, resource_2_quantity=0)
    src = scenarios.save(scn, str(tmp_path / "a.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        trigger, = aoe2mc.read_scenario(src)[4]["triggers"]
    trigger["id"] = 7
    assert aoe2mc.trigger_files([trigger], 4, np.full((64, 64), 70, np.int16))[1][
        "data/aoe2mc/function/trigger/7.mcfunction"].splitlines()[-1] == \
        'data modify storage aoe2mc:costs list append value "1 LOOM gold=100"'


def test_a_technology_with_no_name_has_no_lines():
    assert lines([[GOLD, 100]], "999") == [] and lines([[GOLD, 100]], None) == []


def test_the_menu_shows_the_trigger_cost_of_loom():
    _, g = setup("BRITONS")
    before = train.price(g, "LOOM")
    costs(g, '["1 LOOM gold=100", "2 LOOM gold=1"]')
    assert train.price(g, "LOOM") == {"gold": 100} != before
    _, other = setup("BRITONS")
    assert train.price(other, "LOOM") == before                         # another player keeps the old cost
