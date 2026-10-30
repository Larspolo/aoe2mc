"""#2820 (epic #2538): the trigger effect "Change Technology Research Time" puts the new research time of a technology
of a player into the data storage aoe2mc:times; the scenario mode of the game program uses it when the player
researches. The other players keep the normal time."""
import os
import sys

import numpy as np
from test_civ_costs import setup
from test_scenario_patrol import trigger

import aoe2mc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import scenario  # noqa: E402

from game import train  # noqa: E402


def lines(name="LOOM", quantity=5):
    t = trigger(aoe2mc.CHANGE_TECHNOLOGY_RESEARCH_TIME)
    t["effects"][0].update(technology=name, quantity=quantity)
    return aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16))[1].get(
        "data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_the_trigger_function_stores_the_new_time():
    assert lines() == ['data modify storage aoe2mc:times list append value "1 LOOM 5"']
    assert lines("", 5) == [] and lines("LOOM", -1) == []


def times(g, stored):
    """Run scenario.times with a fake storage that holds the texts of stored; return the RCON log."""
    command, log = g.command, []

    def answer(cmd):
        log.append(cmd)
        if cmd.startswith(f"data get storage {scenario.TIMES}"):
            return f"Storage {scenario.TIMES} has the following contents: {stored}"
        return command(cmd)
    g.command = answer
    scenario.times(g)
    return log


def test_loom_of_player_1_takes_the_trigger_time_and_player_2_keeps_the_normal_time():
    _, g = setup("BRITONS")
    _, other = setup("BRITONS")
    normal = train.seconds(g, "LOOM")
    log = times(g, '["1 LOOM 5", "2 LOOM 1"]')
    assert f"data remove storage {scenario.TIMES} list" in log
    assert train.seconds(g, "LOOM") == 5 != normal
    assert train.seconds(other, "LOOM") == normal


def test_an_empty_storage_changes_no_time():
    _, g = setup("BRITONS")
    log = times(g, "[]")
    assert not any(c.startswith("data remove") for c in log) and "trigger_times" not in vars(g)
