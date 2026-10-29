"""Live replay: the army of each player in the book "Army" (#3696, #3924). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_stat_books import page  # noqa: E402

TC = {"kind": "building", "name": "TOWN_CENTER", "player": 1, "ref": 5, "tile": [8.0, 8.0], "footprint": [26, 26, 38, 38]}


def make(timeline=()):
    d = data(list(timeline))
    d["objects"].append(TC)
    return replay.Replay(Fake(), d)


def test_the_first_call_gives_a_page_per_player_and_a_second_call_sends_nothing():
    r = make()
    r.troop(1, "KNIGHT")
    r.troop(1, "KNIGHT")
    r.troop(1, "ARCHER")
    first = r.army_view(0)
    assert len(first) == 1 and first[0].startswith(f"item replace entity @a hotbar.{replay.STAT_BOOKS['Army']} ")
    assert page(first, 0)[0] == "Army: 2 Knight, 1 Archer" and page(first, 1)[0] == "Army: -"
    assert r.army_view(0) == []                                      # the same counts: no command


def test_a_change_of_the_army_changes_the_book():
    r = make()
    r.troop(1, "KNIGHT")
    r.army_view(0)
    r.troop(1, "KNIGHT")
    (cmd,) = r.army_view(1000)
    assert page([cmd], 0)[0] == "Army: 2 Knight"


def test_a_unit_in_training_and_the_losses_show_until_the_training_ends():
    r = make([{"time": 0, "player": 1, "kind": "queue", "type": 83, "objects": [5], "name": "KNIGHT"}])
    r.fallen[1] = {"ARCHER": 3, "KNIGHT": 2}
    assert page(r.army_view(500), 0)[:3] == ["Army: -", "Training: 1 Knight", "Lost: 5"]
    end = r.trainings[0][0]
    assert page(r.army_view(end), 0)[:2] == ["Army: -", "Lost: 5"]  # the unit is out: the training goes
