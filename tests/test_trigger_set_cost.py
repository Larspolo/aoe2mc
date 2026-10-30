"""#2857 (epic #2538): the trigger effect "Set Object Cost" sets one resource of the cost of a unit or building type. The
converter writes the resource with a "+" in front of it; the scenario mode of the game program keeps the other
resources of the cost."""
import os
import sys

import numpy as np
from test_civ_costs import setup
from test_scenario_patrol import trigger

import aoe2mc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import scenario  # noqa: E402

from game import train  # noqa: E402

FOOD, WOOD, STONE, GOLD = range(4)


def lines(cost, name=("U", "MILITIA")):
    t = trigger(aoe2mc.SET_OBJECT_COST)
    t["effects"][0].update(object=name, cost=cost)
    return aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16))[1].get(
        "data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_the_trigger_function_stores_the_one_resource():
    assert lines([[GOLD, 5]]) == [
        'data modify storage aoe2mc:costs list append value "1 MILITIA +gold=5"']


def test_an_effect_with_no_object_has_no_lines():
    assert lines([[GOLD, 5]], None) == []


def costs(g, stored):
    """Run scenario.costs with a fake storage that holds the texts of stored."""
    command = g.command

    def answer(cmd):
        if cmd.startswith(f"data get storage {scenario.COSTS}"):
            return f"Storage {scenario.COSTS} has the following contents: {stored}"
        return command(cmd)
    g.command = answer
    scenario.costs(g)


def test_the_player_pays_the_one_resource_and_keeps_the_rest():
    server, g = setup("GOTHS", food=100, gold=50)
    before = train.price(g, "VILLAGER_MALE")
    costs(g, '["1 VILLAGER_MALE +gold=5"]')
    assert train.price(g, "VILLAGER_MALE") == {**before, "gold": 5}
    assert train.queue(g, "Steve", (3, 3)) and g.stock["food"] == 100 - before["food"]
    assert g.stock["gold"] == 45
