"""#2865 (epic #2538): the trigger effect "Add Train Location" puts a unit, a building, a button and a train time of a
player into the data storage aoe2mc:locations; the scenario mode of the game program adds the unit to the menu of that
building of that player."""
import os
import sys

import numpy as np

import aoe2mc
from test_civ_costs import setup
from test_forging import menus
from test_scenario_patrol import trigger
from tools import triggers

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import scenario  # noqa: E402
from game import train  # noqa: E402


def lines(unit="MILITIA", building="CASTLE", player=1, button=5, seconds=10):
    t = trigger(aoe2mc.ADD_TRAIN_LOCATION)
    t["effects"][0].update(object=unit and ("U", unit), building=building and ("B", building), player=player,
                           button=button, seconds=seconds)
    return aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16))[1].get(
        "data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_the_trigger_function_stores_the_train_location():
    assert lines() == ['data modify storage aoe2mc:locations list append value "1 MILITIA CASTLE 5 10"']
    assert lines(button=-1, seconds=-1) == ['data modify storage aoe2mc:locations list append value "1 MILITIA CASTLE 0 0"']


def test_no_unit_no_building_or_gaia_gives_no_line():
    assert lines(unit=None) == [] and lines(building=None) == [] and lines(player=0) == []


def locations(g, stored):
    """Run scenario.locations with a fake storage that holds stored; return the RCON log."""
    command, log = g.command, []

    def answer(cmd):
        log.append(cmd)
        if cmd.startswith(f"data get storage {scenario.LOCATIONS}"):
            return f"Storage {scenario.LOCATIONS} has the following contents: {stored}"
        return command(cmd)
    g.command = answer
    scenario.locations(g)
    return log


def castle(civ="BRITONS"):
    """setup() with a built castle at blocks x 2-6, z 10-14 and a built barracks at x 10-12, z 10-12."""
    server, g = setup(civ)
    g.sites += [{"name": "CASTLE", "player": 1, "footprint": [2, 7, 10, 15], "done": True},
                {"name": "BARRACKS", "player": 1, "footprint": [10, 13, 10, 13], "done": True}]
    return server, g


def test_the_castle_menu_of_the_player_has_the_militia_with_its_time():
    server, g = castle()
    log = locations(g, '["1 MILITIA CASTLE 5 10", "2 MILITIA CASTLE 1 10"]')
    assert f"data remove storage {scenario.LOCATIONS} list" in log
    assert g.trigger_trains == {"CASTLE": {"MILITIA": (5, 10)}}       # player 2: not this side
    train.open_menu(g, "Steve", (3, 11))
    assert ":Militia:" in menus(server)[-1] and "· 10 s ·" in menus(server)[-1].split(":Militia:")[1]
    assert train.placed(g, "CASTLE", "MILITIA")[0] == 5                # AoE2 button 5: slot 4, Sappers has it
    train.open_menu(g, "Steve", (11, 11))
    assert ":Militia:" in menus(server)[-1]                             # the barracks keeps its item
    assert train.seconds(g, "MILITIA", "BARRACKS") == 21
    server, h = castle()                                               # player 2 has no militia in the castle
    train.open_menu(h, "Steve", (3, 11))
    assert ":Militia:" not in menus(server)[-1]


def test_a_click_on_the_slot_queues_the_militia_at_the_castle():
    _, g = castle()
    g.stock.update(food=100, gold=100)
    locations(g, '["1 MILITIA CASTLE 11 10"]')
    slot = train.placed(g, "CASTLE", "MILITIA")[0]
    assert slot == train.MORE + 9                                      # the third row of AoE2: under the queue row
    rect = train.home(g, (3, 11))
    assert train.order(g, "Steve", rect, slot) == 1 and g.queues[rect][0]["name"] == "MILITIA"


def test_a_taken_slot_moves_the_item_to_the_next_free_slot():
    _, g = castle()
    locations(g, '["1 MILITIA CASTLE 2 0"]')                           # slot 1: the trebuchet
    own = {train.slots("CASTLE", n)[0] for n in train.trains(g, "CASTLE") if n != "MILITIA"}
    assert train.placed(g, "CASTLE", "MILITIA")[0] not in own
    assert train.seconds(g, "MILITIA", "CASTLE") == 21                 # no time: the time of the unit


def test_an_empty_storage_adds_no_location():
    _, g = setup("BRITONS")
    log = locations(g, "[]")
    assert not any(c.startswith("data remove") for c in log) and "trigger_trains" not in vars(g)


def test_the_map_row_names_the_command_and_the_issue():
    row = triggers.MAP[("effect", "ADD_TRAIN_LOCATION")]
    assert "aoe2mc:locations" in row and "#2865" in row
