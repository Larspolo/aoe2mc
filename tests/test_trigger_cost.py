"""#2776 (epic #2538): the trigger effect "Change Object Cost" puts the new cost of a unit or building type of a player
into the data storage aoe2mc:costs; the scenario mode of the game program uses it in the menus and when the player
pays. The other players keep the old cost."""
import os
import sys

import numpy as np
from test_civ_costs import setup
from test_scenario_patrol import trigger

import aoe2mc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import scenario  # noqa: E402

from game import build, train  # noqa: E402

FOOD, WOOD, STONE, GOLD = range(4)


def lines(cost, name=("U", "MILITIA")):
    t = trigger(aoe2mc.CHANGE_OBJECT_COST)
    t["effects"][0].update(object=name, cost=cost)
    return aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16))[1].get(
        "data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_the_trigger_function_stores_the_new_cost():
    assert lines([[FOOD, 20], [GOLD, 0], [FOOD, 0]]) == [
        'data modify storage aoe2mc:costs list append value "1 MILITIA food=20"']
    assert lines([[WOOD, 75], [STONE, 10], [-1, 5]], ("B", "HOUSE"))[0].endswith('"1 HOUSE wood=75 stone=10"')


def test_an_effect_with_no_object_has_no_lines():
    assert lines([[FOOD, 20]], None) == []


def costs(g, stored):
    """Run scenario.costs with a fake storage that holds the texts of stored; return the RCON log."""
    command, log = g.command, []

    def answer(cmd):
        log.append(cmd)
        if cmd.startswith(f"data get storage {scenario.COSTS}"):
            return f"Storage {scenario.COSTS} has the following contents: {stored}"
        return command(cmd)
    g.command = answer
    scenario.costs(g)
    return log


def test_the_player_pays_the_trigger_cost():
    server, g = setup("GOTHS", food=100, gold=50)
    log = costs(g, '["1 VILLAGER_MALE food=20 gold=5", "2 VILLAGER_MALE food=1"]')
    assert f"data remove storage {scenario.COSTS} list" in log
    assert train.price(g, "VILLAGER_MALE") == {"food": 20, "gold": 5}
    assert train.queue(g, "Steve", (3, 3)) and g.stock["food"] == 80 and g.stock["gold"] == 45


def test_the_build_menu_shows_the_trigger_cost_of_a_building():
    _, g = setup("BRITONS")
    before = build.price(g, "HOUSE")
    costs(g, '["1 HOUSE stone=10"]')
    assert build.price(g, "HOUSE") == {"stone": 10} != before
    assert build.price(g, "HOUSE", player=2) == before                  # another player keeps the old cost


def test_an_empty_storage_changes_no_cost():
    _, g = setup("BRITONS")
    log = costs(g, "[]")
    assert not any(c.startswith("data remove") for c in log) and "trigger_costs" not in vars(g)
