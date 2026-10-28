"""A pause or a new speed of a live replay reaches each walking unit of the plugin, not only `Replay.moving` (#3024)."""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_replay import Fake, data  # noqa: E402

import ai  # noqa: E402
import replay  # noqa: E402


def walker(i, end):
    """A unit on one plugin leg that ends at game time `end` (ms), not in Replay.moving."""
    return types.SimpleNamespace(uuid=f"u{i}", name="VILLAGER", leg=((0, 0), 0, end))


def test_a_pause_stops_a_unit_on_its_last_leg():
    r = replay.Replay(Fake(), data([]), ai=True)
    r.control, r.units, r.moving = {"speed": 1.0, "paused": True}, {7: walker(7, 5000)}, {}
    r.retime(1000, 0.0, 2.0)                                           # game time 3000 at the change
    assert r.game.sent == [ai.speed_command("u7", "VILLAGER", r.T, 0)]


def test_a_speed_change_sets_the_walk_speed_with_the_path_factor():
    r = replay.Replay(Fake(), data([]), ai=True)
    r.control, r.units, r.moving = {"speed": 8.0, "paused": False}, {7: walker(7, 5000)}, {}
    r.retime(1000, 0.0, 2.0)
    assert r.game.sent == [ai.speed_command("u7", "VILLAGER", r.T, 8 * replay.PATH)]


def test_a_unit_whose_leg_ended_gets_no_command():
    r = replay.Replay(Fake(), data([]), ai=True)
    r.control, r.units, r.moving = {"speed": 8.0, "paused": False}, {7: walker(7, 2000)}, {}
    r.retime(1000, 0.0, 2.0)                                           # game time 3000: the leg ended at 2000
    assert r.game.sent == []
