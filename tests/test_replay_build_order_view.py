"""Live replay: the build order of each player in the book "Army" (#4049, #3924). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_stat_books import page  # noqa: E402


def make(timeline=()):
    return replay.Replay(Fake(), data(list(timeline)))


def build(t, name, player=1):
    return {"time": t, "player": player, "kind": "build", "name": name}


def order(cmds, k=0):
    """The build order lines of page k of the book "Army"."""
    lines = page(cmds, k)
    return lines[lines.index("Build order:") + 1:]


def test_the_first_call_gives_the_steps_of_each_player_and_a_second_call_sends_nothing():
    r = make([build(60000, "HOUSE")])
    first = r.army_view(60000)
    assert order(first, 0) == ["01:00 House"] and order(first, 1) == ["-"]
    assert r.army_view(60000) == []


def test_a_new_step_changes_the_book():
    r = make([build(60000, "HOUSE"), build(90000, "MILL")])
    r.army_view(60000)
    assert order(r.army_view(90000)) == ["01:00 House", "01:30 Mill"]


def test_the_book_shows_at_most_4_steps():
    names = ["HOUSE", "MILL", "LUMBER_CAMP", "BARRACKS", "BLACKSMITH"]
    r = make([build(60000 * (i + 1), n) for i, n in enumerate(names)])
    lines = order(r.army_view(600000))
    assert len(lines) == 4 and "01:00 House" not in lines and lines[-1] == "05:00 Blacksmith"
