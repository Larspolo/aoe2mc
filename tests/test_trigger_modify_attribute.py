"""#2763 (epic #2538): the trigger effect "Modify Attribute" puts a change of a combat value of a unit type of a player
into the data storage aoe2mc:attributes; the scenario mode of the game program changes train.stats of that player and
sends the new values to the units of the type that exist."""
import os
import sys

import numpy as np
import pytest

import aoe2mc
from test_civ_costs import setup
from test_scenario_patrol import trigger

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import scenario  # noqa: E402
from game import train  # noqa: E402

HIT_POINTS, ARMOR, ATTACK, MAXIMUM_RANGE, LINE_OF_SIGHT = 0, 8, 9, 12, 1
SET, ADD, SUBTRACT, MULTIPLY, DIVIDE = range(1, 6)


def lines(attribute, operation, quantity, cls=-1, aa=-1):
    t = trigger(aoe2mc.MODIFY_ATTRIBUTE)
    t["effects"][0].update(object=("U", "ARCHER"), attribute=attribute, operation=operation, quantity=quantity,
                           **{"class": cls}, aa=aa)
    return aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16))[1].get(
        "data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_the_trigger_function_stores_the_change():
    assert lines(HIT_POINTS, ADD, 10) == ['data modify storage aoe2mc:attributes list append value "1 ARCHER hp 2 10"']
    assert lines(ARMOR, SUBTRACT, -1, cls=3, aa=1)[0].endswith('"1 ARCHER pierce 3 1"')
    assert lines(MAXIMUM_RANGE, SET, 5.5)[0].endswith('"1 ARCHER range 1 5.5"')


def test_an_attribute_that_the_game_program_does_not_have_has_no_lines():
    assert lines(LINE_OF_SIGHT, ADD, 2) == []
    assert lines(ATTACK, ADD, -1, cls=27, aa=2) == []                   # a bonus class


def apply(g, stored):
    """Run scenario.attributes with a fake storage that holds the texts of stored; return the RCON log."""
    command, log = g.command, []

    def answer(cmd):
        log.append(cmd)
        if cmd.startswith(f"data get storage {scenario.ATTRIBUTES}"):
            return f"Storage {scenario.ATTRIBUTES} has the following contents: {stored}"
        return command(cmd)
    g.command = answer
    scenario.attributes(g)
    return log


def test_the_archers_of_the_player_get_more_hit_points():
    _, g = setup("BRITONS")
    _, other = setup("BRITONS")
    before = train.stats(g, "ARCHER").hp
    g.units.append({"uuid": "u1", "name": "ARCHER"})
    log = apply(g, '["1 ARCHER hp 2 10", "2 ARCHER hp 2 99"]')
    assert f"data remove storage {scenario.ATTRIBUTES} list" in log
    assert train.stats(g, "ARCHER").hp == before + 10 and train.stats(other, "ARCHER").hp == before
    assert any(c.startswith(f"aoe stats u1 {before + 10} ") for c in log)
    assert train.stats(g, "SKIRMISHER") == train.stats(other, "SKIRMISHER")


@pytest.mark.parametrize("op, q, hp", [(SET, 50, 50), (ADD, 10, 40), (SUBTRACT, 5, 25), (MULTIPLY, 2, 60),
                                       (DIVIDE, 4, 7), (SUBTRACT, 99, 0)])
def test_each_operation_gives_the_aoe2_result(op, q, hp):
    _, g = setup("BRITONS")
    assert train.stats(g, "ARCHER").hp == 30
    apply(g, f'["1 ARCHER hp {op} {q}"]')
    assert train.stats(g, "ARCHER").hp == hp


def test_a_range_change_sends_the_range_of_the_archers():
    _, g = setup("BRITONS")
    g.soldiers["u2"] = "ARCHER"
    log = apply(g, '["1 ARCHER range 1 6.5"]')
    assert train.stats(g, "ARCHER").range == 6.5
    assert any(c.startswith("aoe stats u2 ") for c in log) and any(c.startswith("aoe range u2 ") for c in log)
