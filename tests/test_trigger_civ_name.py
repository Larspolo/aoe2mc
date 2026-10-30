"""#2905 (epic #2538): the trigger effect "Change Civilization Name" puts the new civilization name of a player into the
list "civs" of the data storage aoe2mc:names; the scenario mode of the game program shows it next to the player name."""
import os
import sys

import numpy as np
from test_civ_costs import setup
from test_scenario_patrol import trigger

import aoe2mc
from tools import triggers

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import diplomacy  # noqa: E402
import lobby  # noqa: E402
import scenario  # noqa: E402


def lines(message, player=1):
    t = trigger(aoe2mc.CHANGE_CIVILIZATION_NAME)
    t["effects"][0].update(message=message, player=player)
    return aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16))[1].get(
        "data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_the_trigger_function_stores_the_new_name():
    assert lines("Northmen") == ['data modify storage aoe2mc:names civs append value "1 Northmen"']
    assert lines('<red>The "Sea" \\ Folk') == [
        'data modify storage aoe2mc:names civs append value "1 The \\"Sea\\" \\\\ Folk"']   # escaped, no tags


def test_no_text_or_gaia_gives_no_line():
    assert lines("") == [] and lines("X", player=0) == []


def civ_names(g, stored):
    """Run scenario.civ_names with a fake storage that holds stored; return the RCON log."""
    command, log = g.command, []

    def answer(cmd):
        log.append(cmd)
        if cmd.startswith(f"data get storage {scenario.NAMES} civs"):
            return f"Storage {scenario.NAMES} has the following contents: {stored}"
        return command(cmd)
    g.command = answer
    scenario.civ_names(g)
    return log


def test_the_player_list_and_the_diplomacy_page_show_the_new_name():
    _, g = setup("BRITONS")
    g.players["2"] = {"civ": "FRANKS", "color": "red"}
    log = civ_names(g, '["2 Old Name", "2 Northmen", \'1 The "Sea" Folk\']')
    assert f"data remove storage {scenario.NAMES} civs" in log
    assert g.trigger_civs == {"1": 'The "Sea" Folk', "2": "Northmen"}   # a later line wins
    assert diplomacy.name(g, 2) == "Player 2 (Northmen)" and lobby.name(g, 1) == 'Player 1 (The "Sea" Folk)'
    _, h = setup("BRITONS")                                            # no trigger: the civilization
    assert lobby.name(h, 1) == "Player 1 (Britons)" and diplomacy.name(h, 1) == "Player 1 (Britons)"


def test_an_empty_storage_changes_no_name():
    _, g = setup("BRITONS")
    log = civ_names(g, "[]")
    assert not any(c.startswith("data remove") for c in log) and "trigger_civs" not in vars(g)


def test_the_map_row_names_the_command_and_the_issue():
    row = triggers.MAP[("effect", "CHANGE_CIVILIZATION_NAME")]
    assert "aoe2mc:names civs" in row and "#2905" in row
