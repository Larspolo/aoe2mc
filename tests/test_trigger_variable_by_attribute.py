"""#2858 (epic #2538): the trigger effect "Modify Variable by Attribute" puts a request into the data storage
aoe2mc:reads; the scenario mode of the game program changes the score #v<N> of aoe_var by the value of the unit type of
the player (train.stats) with a scoreboard operation."""
import os
import re
import sys

import numpy as np
import pytest

import aoe2mc
from test_civ_costs import setup
from test_scenario_patrol import trigger

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import scenario  # noqa: E402

HIT_POINTS, ARMOR, LINE_OF_SIGHT = 0, 8, 1
SET, ADD, SUBTRACT = 1, 2, 3


def lines(attribute=HIT_POINTS, operation=SET, variable=4, cls=-1):
    t = trigger(aoe2mc.MODIFY_VARIABLE_BY_ATTRIBUTE)
    t["effects"][0].update(object=("U", "MILITIA"), attribute=attribute, operation=operation, variable=variable,
                           **{"class": cls})
    load, files = aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16))
    return load, files.get("data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_the_trigger_function_stores_the_request():
    load, out = lines()
    assert out == ['data modify storage aoe2mc:reads list append value "1 MILITIA hp 1 4"']
    assert "scoreboard players add #v4 aoe_var 0" in load                # the variable starts at 0
    assert lines(ARMOR, ADD, 2, cls=3)[1][0].endswith('"1 MILITIA pierce 2 2"')


def test_an_attribute_that_the_game_program_does_not_have_has_no_lines():
    assert lines(LINE_OF_SIGHT)[1] == []
    assert lines(variable=-1)[1] == []


def run(g, stored, scores):
    """Run scenario.reads with a fake storage that holds the texts of stored and a fake scoreboard aoe_var."""
    command = g.command

    def answer(cmd):
        if cmd.startswith(f"data get storage {scenario.READS}"):
            return f"Storage {scenario.READS} has the following contents: {stored}"
        if m := re.fullmatch(r"scoreboard players set (\S+) aoe_var (-?\d+)", cmd):
            scores[m[1]] = int(m[2])
        elif m := re.fullmatch(r"scoreboard players operation (\S+) aoe_var ([-+*/]?)= (\S+) aoe_var", cmd):
            a, b = scores.get(m[1], 0), scores[m[3]]
            scores[m[1]] = {"": b, "+": a + b, "-": a - b, "*": a * b, "/": a // b}[m[2]]
        return command(cmd)
    g.command = answer
    scenario.reads(g)
    return scores


@pytest.mark.parametrize("op, before, after", [(SET, 7, 40), (ADD, 2, 42), (SUBTRACT, 50, 10)])
def test_the_variable_gets_the_militia_hit_points(op, before, after):
    _, g = setup("BRITONS")
    assert run(g, f'["1 MILITIA hp {op} 4"]', {"#v4": before})["#v4"] == after


def test_a_request_of_another_player_does_not_change_the_variable():
    _, g = setup("BRITONS")
    assert run(g, '["5 MILITIA hp 1 4"]', {"#v4": 3})["#v4"] == 3
