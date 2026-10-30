"""Live replay: the players are named by the name of the record (#4668), else "Player N". A fake game."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_control import Clock  # noqa: E402


def named(info):
    d = data([])
    d["players"] = {"1": info}
    return replay.Replay(Clock(), d).player(1)


def test_the_name_of_the_record_replaces_player_n():
    assert named({"civ": "BRITONS", "color": "blue", "name": "Alice"}) == ("Alice (Britons)", replay.TEXT_COLORS["blue"])


def test_without_a_name_the_player_keeps_its_number():
    assert named({"civ": "BRITONS", "color": "blue"}) == ("Player 1 (Britons)", replay.TEXT_COLORS["blue"])


def test_a_long_name_is_cut_to_15_characters_and_an_ellipsis():
    name, _ = named({"civ": "BRITONS", "color": "blue", "name": "A" * 20})
    assert name == "A" * 15 + "… (Britons)"
