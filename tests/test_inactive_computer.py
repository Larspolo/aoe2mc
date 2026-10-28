"""A player slot above the player count of a scenario is not a computer player, even when the designer set it to
"Computer" (#3110): the scenario mode seats no bot there."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import scenario  # noqa: E402

import aoe2mc  # noqa: E402
import scenarios  # noqa: E402


def convert(tmp_path, computer):
    """A scenario of 2 active players. Each slot in `computer` is set to Computer (human False)."""
    scn = scenarios.new_scenario(24)
    for n in computer:
        scn.player_manager.players[n].human = False
    src = scenarios.save(scn, str(tmp_path / "s.aoe2scenario"))
    aoe2mc.main([src, str(tmp_path / "W")])
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        return json.load(f)["players"]


def test_an_inactive_slot_set_to_computer_is_no_computer_player(tmp_path):
    players = convert(tmp_path, [5])
    assert players["5"].get("computer") is not True
    assert scenario.bot_seats(players, people=1) == []


def test_an_active_slot_set_to_computer_is_a_computer_player(tmp_path):
    players = convert(tmp_path, [2])
    assert players["2"]["computer"] is True
    assert scenario.bot_seats(players, people=1) == [(2, 1)]
