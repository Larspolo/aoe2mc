"""#2866 (epic #2538): the trigger effects "Enable Technology Stacking" and "Disable Technology Stacking" put
"<player> <technology> stack <n>" into the data storage aoe2mc:menus; the scenario mode of the game program lets the
player research the technology n times, and the effects stack."""
import os
import sys

import numpy as np

import aoe2mc
from test_forging import menus, setup
from test_scenario_patrol import trigger
from tools import triggers

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import scenario  # noqa: E402
from game import combat, train  # noqa: E402


def lines(kind, tech="FORGING", player=1, **keys):
    t = trigger(kind)
    t["effects"][0].update(technology=tech, player=player, **keys)
    return aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16))[1].get(
        "data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_both_effects_go_into_the_storage():
    assert lines(aoe2mc.ENABLE_TECHNOLOGY_STACKING, quantity=2) == [
        'data modify storage aoe2mc:menus list append value "1 FORGING stack 2"']
    assert lines(aoe2mc.DISABLE_TECHNOLOGY_STACKING) == [
        'data modify storage aoe2mc:menus list append value "1 FORGING stack 1"']
    assert lines(aoe2mc.ENABLE_TECHNOLOGY_STACKING, quantity=0) == []
    assert lines(aoe2mc.DISABLE_TECHNOLOGY_STACKING, tech="") == [] and lines(aoe2mc.DISABLE_TECHNOLOGY_STACKING, player=0) == []


def stacks(g, stored):
    command = g.command
    g.command = lambda cmd: (f"Storage {scenario.MENUS} has the following contents: {stored}"
                             if cmd.startswith(f"data get storage {scenario.MENUS}") else command(cmd))
    scenario.menus(g)
    g.command = command


def research(g, server):
    rect = train.open_menu(g, "Steve", (11, 3))
    assert train.order(g, "Steve", rect, 0) == 1
    train.tick(g, 50)
    return menus(server)[-1]


def test_stacking_two_researches_forging_twice_then_hides_it():
    server, g = setup(food=1000)
    stacks(g, '["1 FORGING stack 2", "2 FORGING stack 5"]')
    assert g.trigger_stacks == {"FORGING": 2}
    research(g, server)
    assert train.stats(g, "MILITIA").attack == combat.stats("MILITIA").attack + 1
    train.open_menu(g, "Steve", (11, 3))
    assert ":Forging:" in menus(server)[-1]
    research(g, server)
    assert train.stats(g, "MILITIA").attack == combat.stats("MILITIA").attack + 2 and train.count(g, "FORGING") == 2
    train.open_menu(g, "Steve", (11, 3))
    assert ":Forging:" not in menus(server)[-1]


def test_disable_stacking_keeps_one_research():
    server, g = setup(food=1000)
    stacks(g, '["1 FORGING stack 2", "1 FORGING stack 1"]')
    research(g, server)
    train.open_menu(g, "Steve", (11, 3))
    assert ":Forging:" not in menus(server)[-1]


def test_the_map_rows_name_the_command_and_the_issue():
    for kind in ("ENABLE_TECHNOLOGY_STACKING", "DISABLE_TECHNOLOGY_STACKING"):
        row = triggers.MAP[("effect", kind)]
        assert "aoe2mc:menus" in row and "#2866" in row
