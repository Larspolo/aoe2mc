"""#2864 (epic #2538): the trigger effects "Change Train Location" and "Change Technology Location" put the new place
(building and AoE2 button) of a unit or technology of a player into the data storage aoe2mc:places; the scenario mode
of the game program moves the item to the menu of that building, for that player only."""
import contextlib
import io
import os
import sys

import numpy as np

import aoe2mc
from test_civ_costs import setup
from test_forging import menus
from test_scenario_patrol import trigger
from tools import scenarios, triggers

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import scenario  # noqa: E402
from game import train  # noqa: E402


def lines(kind, name="SCOUT_CAVALRY", building="TOWN_CENTER", button=4, player=1):
    t = trigger(kind)
    t["effects"][0].update(player=player, object2=("U", building), button=button,
                           **({"object": ("U", name)} if kind == aoe2mc.CHANGE_TRAIN_LOCATION else {"technology": name}))
    return aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16))[1].get(
        "data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_the_trigger_function_stores_the_new_place():
    assert lines(aoe2mc.CHANGE_TRAIN_LOCATION) == [
        'data modify storage aoe2mc:places list append value "1 SCOUT_CAVALRY TOWN_CENTER 4"']
    assert lines(aoe2mc.CHANGE_TECHNOLOGY_LOCATION, "LOOM", "STABLE", 9) == [
        'data modify storage aoe2mc:places list append value "1 LOOM STABLE 9"']


def test_no_unit_no_building_or_gaia_gives_no_line():
    assert lines(aoe2mc.CHANGE_TECHNOLOGY_LOCATION, "") == []
    assert lines(aoe2mc.CHANGE_TRAIN_LOCATION, building="") == []
    assert lines(aoe2mc.CHANGE_TRAIN_LOCATION, player=0) == []


def places(g, stored):
    """Run scenario.places with a fake storage that holds stored; return the RCON log."""
    command, log = g.command, []
    def answer(cmd):
        log.append(cmd)
        if cmd.startswith(f"data get storage {scenario.PLACES}"):
            return f"Storage {scenario.PLACES} has the following contents: {stored}"
        return command(cmd)
    g.command = answer
    scenario.places(g)
    return log


def test_the_menus_of_the_player_show_the_item_in_its_new_building():
    server, g = setup("BRITONS", food=200)
    log = places(g, '["1 SCOUT_CAVALRY TOWN_CENTER 6", "2 LOOM STABLE 1", "1 LOOM STABLE 9"]')
    assert f"data remove storage {scenario.PLACES} list" in log
    assert g.trigger_places == {"SCOUT_CAVALRY": ["TOWN_CENTER", 6], "LOOM": ["STABLE", 9]}   # player 2: not this side
    assert "SCOUT_CAVALRY" in train.trains(g, "TOWN_CENTER") and "LOOM" not in train.trains(g, "TOWN_CENTER")
    assert "SCOUT_CAVALRY" not in train.trains(g, "STABLE") and "LOOM" in train.trains(g, "STABLE")
    assert train.placed(g, "TOWN_CENTER", "SCOUT_CAVALRY")[0] == 5                # button 6: the 6th slot of the first row
    assert train.placed(g, "STABLE", "LOOM")[0] == train.MORE                     # button 9: the row under the queue
    train.open_menu(g, "Steve", (3, 3))
    assert ":Scout Cavalry:" in menus(server)[-1] and ":Loom:" not in menus(server)[-1]
    assert ":Imperial Age:" not in menus(server)[-1]                  # the moved item takes its slot 5
    assert train.order(g, "Steve", next(r for r in train.homes(g) if train.homes(g)[r] == "TOWN_CENTER"), 5) == 1
    assert g.queues[(2, 5, 2, 5)][-1]["name"] == "SCOUT_CAVALRY" and g.stock["food"] == 120
    train.open_menu(g, "Steve", (11, 3))
    assert ":Loom:" in menus(server)[-1] and ":Scout Cavalry:" not in menus(server)[-1]


def test_another_player_keeps_the_old_places():
    server, h = setup("BRITONS")
    train.open_menu(h, "Steve", (3, 3))
    assert ":Loom:" in menus(server)[-1] and ":Scout Cavalry:" not in menus(server)[-1]


def test_an_empty_storage_moves_nothing():
    _, g = setup("BRITONS")
    log = places(g, "[]")
    assert not any(c.startswith("data remove") for c in log) and "trigger_places" not in vars(g)


def test_read_scenario_keeps_the_building_and_the_button(tmp_path):
    scn = scenarios.new_scenario(16)
    t = scn.trigger_manager.add_trigger("Move")
    t.new_condition.timer(timer=1)
    t.new_effect.change_train_location(object_list_unit_id=448, source_player=1, object_list_unit_id_2=109,
                                       button_location=6)
    t.new_effect.change_technology_location(technology=22, source_player=1, object_list_unit_id_2=101, button_location=2)
    src = scenarios.save(scn, str(tmp_path / "a.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        trigger_, = aoe2mc.read_scenario(src)[4]["triggers"]
    unit, tech = trigger_["effects"]
    assert unit["object"][1] == "SCOUT_CAVALRY" and unit["object2"][1] == "TOWN_CENTER" and unit["button"] == 6
    assert tech["technology"] == "LOOM" and tech["object2"][1] == "STABLE" and tech["button"] == 2


def test_the_map_rows_name_the_command_and_the_issue():
    for kind in ("CHANGE_TRAIN_LOCATION", "CHANGE_TECHNOLOGY_LOCATION"):
        row = triggers.MAP[("effect", kind)]
        assert "aoe2mc:places" in row and "#2864" in row
