"""#2821 (epic #2538): the trigger effect "Change Technology Name" puts the new name of a technology of a player into
the data storage aoe2mc:names; the scenario mode of the game program shows it in the menus of that player."""
import os
import sys

import numpy as np
from test_civ_costs import setup
from test_forging import menus
from test_scenario_patrol import trigger

import aoe2mc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import scenario  # noqa: E402

from game import train  # noqa: E402


def lines(message, tech="LOOM", player=1):
    t = trigger(aoe2mc.CHANGE_TECHNOLOGY_NAME)
    t["effects"][0].update(message=message, technology=tech, player=player)
    return aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16))[1].get(
        "data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_the_trigger_function_stores_the_new_name():
    assert lines("Old Wisdom") == ['data modify storage aoe2mc:names list append value "1 LOOM Old Wisdom"']
    assert lines('<blue>The "Old" \\ Way') == [
        'data modify storage aoe2mc:names list append value "1 LOOM The \\"Old\\" \\\\ Way"']   # escaped, no tags


def test_no_text_no_technology_or_gaia_gives_no_line():
    assert lines("") == [] and lines("X", tech="") == [] and lines("X", player=0) == []


def names(g, stored):
    """Run scenario.names with a fake storage that holds stored; return the RCON log."""
    command, log = g.command, []

    def answer(cmd):
        log.append(cmd)
        if cmd.startswith(f"data get storage {scenario.NAMES}"):
            return f"Storage {scenario.NAMES} has the following contents: {stored}"
        return command(cmd)
    g.command = answer
    scenario.names(g)
    return log


def test_the_menu_of_the_player_shows_the_new_name():
    server, g = setup("BRITONS")
    log = names(g, '["1 LOOM Old Wisdom", "2 LOOM Other Name", \'1 WHEELBARROW The "Cart"\']')
    assert f"data remove storage {scenario.NAMES} list" in log
    assert g.trigger_names == {"LOOM": "Old Wisdom", "WHEELBARROW": 'The "Cart"'}   # player 2: not this side
    loom = next(r["label"] for r in train.ROWS if r["name"] == "LOOM")   # the name of game/data/train.jsonl
    train.open_menu(g, "Steve", (3, 3))
    assert ":Old Wisdom:" in menus(server)[-1] and f":{loom}:" not in menus(server)[-1]
    server, h = setup("BRITONS")                                       # another player sees the old name
    train.open_menu(h, "Steve", (3, 3))
    assert f":{loom}:" in menus(server)[-1]


def test_an_empty_storage_changes_no_name():
    _, g = setup("BRITONS")
    log = names(g, "[]")
    assert not any(c.startswith("data remove") for c in log) and "trigger_names" not in vars(g)

