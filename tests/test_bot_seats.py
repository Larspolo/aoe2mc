"""#4017: `run.py --play --bots N` (or `all`) puts N bots on the player slots after the people."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import run  # noqa: E402

FOUR = {"1": {}, "2": {}, "3": {}, "4": {}}
TEAMS = {"1": {"team": 1}, "2": {"team": 1}, "3": {"team": 2}, "4": {"team": 2}}


def test_bots_take_the_slots_after_the_people():
    assert [p for p, _ in run.bot_seats(FOUR, 1, 3)] == [2, 3, 4]


def test_the_foe_of_each_bot_is_not_its_ally():
    seats = run.bot_seats(TEAMS, 1, "all")
    assert [p for p, _ in seats] == [2, 3, 4]
    assert all(foe is not None and run.bot_foe(TEAMS, p) == foe for p, foe in seats)
    assert dict(seats)[2] == 3


def test_all_gives_the_same_seats_as_the_number_of_free_slots():
    assert run.bot_seats(FOUR, 1, "all") == run.bot_seats(FOUR, 1, 3)


def test_more_bots_than_free_slots_exit_with_the_slot_count():
    with pytest.raises(SystemExit, match="4 player slots"):
        run.bot_seats(FOUR, 1, 5)


def test_bots_count_takes_a_number_or_all():
    assert run.bots_count("2") == 2 and run.bots_count("all") == "all"
    with pytest.raises(Exception):
        run.bots_count("0")


def test_bot_seat_keeps_one_bot_for_the_player_after_the_people():
    assert run.bot_seat(FOUR, 2) == (3, 1)
