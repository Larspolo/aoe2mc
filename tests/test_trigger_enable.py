"""#2775 (epic #2538): the trigger effects "Enable/Disable Object" and "Enable/Disable Technology" put an item of a
player into the data storage aoe2mc:menus; the scenario mode of the game program hides it in the menus of the player,
or shows it also without the civilization or the age."""
import os
import sys

import numpy as np

import aoe2mc
from menu_line import order
from test_civ_costs import setup
from test_scenario_patrol import trigger

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import scenario  # noqa: E402
from game import build, train  # noqa: E402


def lines(kind, enabled, **more):
    t = trigger(kind)
    t["effects"][0].update(enabled=enabled, **more)
    return aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16))[1].get(
        "data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_the_trigger_function_stores_the_item():
    assert lines(aoe2mc.ENABLE_DISABLE_OBJECT, 0, object=("U", "ARCHER")) == [
        'data modify storage aoe2mc:menus list append value "1 ARCHER off"']
    assert lines(aoe2mc.ENABLE_DISABLE_TECHNOLOGY, 1, technology="FLETCHING")[0].endswith('"1 FLETCHING on"')


def test_an_effect_with_no_item_has_no_lines():
    assert lines(aoe2mc.ENABLE_DISABLE_OBJECT, 0) == []
    assert lines(aoe2mc.ENABLE_DISABLE_TECHNOLOGY, -1, technology="FLETCHING") == []


def menus(g, stored):
    """Run scenario.menus with a fake storage that holds the texts of stored; return the RCON log."""
    command, log = g.command, []

    def answer(cmd):
        log.append(cmd)
        if cmd.startswith(f"data get storage {scenario.MENUS}"):
            return f"Storage {scenario.MENUS} has the following contents: {stored}"
        return command(cmd)
    g.command = answer
    scenario.menus(g)
    return log


def labels(g, building):
    return [label for _, label in order(g, building)]


ARCHER, SKIRMISHER, FLETCHING = (train.ITEMS[n][2] for n in ("ARCHER", "SKIRMISHER", "FLETCHING"))


def test_a_disabled_unit_leaves_the_menu_and_comes_back():
    _, g = setup("BRITONS")
    assert ARCHER in labels(g, "ARCHERY_RANGE")
    log = menus(g, '["1 ARCHER off", "2 SKIRMISHER off"]')
    assert f"data remove storage {scenario.MENUS} list" in log
    assert ARCHER not in labels(g, "ARCHERY_RANGE") and SKIRMISHER in labels(g, "ARCHERY_RANGE")
    menus(g, '["1 ARCHER on"]')
    assert ARCHER in labels(g, "ARCHERY_RANGE")


def test_a_disabled_technology_is_not_in_the_menu():
    _, g = setup("BRITONS")
    assert train.unlocked(g, "FLETCHING")
    menus(g, '["1 FLETCHING off"]')
    assert not train.unlocked(g, "FLETCHING") and FLETCHING not in labels(g, "BLACKSMITH")


def test_an_enabled_technology_needs_no_age():
    _, g = setup("BRITONS", feudal=False)
    assert not train.unlocked(g, "FLETCHING")
    menus(g, '["1 FLETCHING on"]')
    assert train.unlocked(g, "FLETCHING")


def test_a_disabled_building_is_not_in_the_build_menu():
    _, g = setup("BRITONS")
    assert not build.hidden(g, "HOUSE")
    menus(g, '["1 HOUSE off"]')
    assert build.hidden(g, "HOUSE") and not build.hidden(g, "MILL")
