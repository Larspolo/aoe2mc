"""--seats (decision #3488: B): two people play one AoE2 player as co-op partners (#3489, epic #3485). Fake server:
`--seats 1,1` puts "Alex" and "Steve" on player 1, and player 2 has no person."""
import os
import sys

import pytest
from test_coop_selection import moved, pick, setup
from test_scenario_mode import game as scenario_game

from game import lobby, run

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import recap  # noqa: E402
import score  # noqa: E402


def make_game(seats):
    g = run.Game.__new__(run.Game)
    g.seats, g.people, g.sides, g.kind, g.spectators, sent = seats, len(seats), {}, "vanilla", frozenset(), []
    g.command = sent.append
    return g, sent


def test_two_people_join_player_1():
    g, sent = make_game(run.seat_list("1,1"))
    g.side("Alex")
    g.side("Steve")
    assert g.sides == {"Alex": 1, "Steve": 1}
    assert "team join p1 Alex" in sent and "team join p1 Steve" in sent
    assert 2 not in g.sides.values()
    g.side("Alex")                                     # a join again keeps the side
    assert g.sides == {"Alex": 1, "Steve": 1}


def test_a_person_after_the_seats_is_a_spectator():
    g, sent = make_game(run.seat_list("1,1,2"))
    for name in ("Alex", "Steve", "Ann", "Bob"):
        g.side(name)
    assert g.sides == {"Alex": 1, "Steve": 1, "Ann": 2}
    assert "team join spec Bob" in sent


def test_the_gather_of_player_1_handles_the_clicks_of_both():
    server, g = setup()
    g.who = "@a[team=p1]"
    pick(g, "Alex", {"m0"})
    pick(g, "Steve", {"m1"})
    server.log.clear()
    g.click("Alex")
    g.click("Steve")
    assert moved(server) == {"m0", "m1"}


def test_the_lobby_lists_the_players_not_the_people():
    g, _ = make_game([1, 1, 2])
    menu = type("G", (), {"game": g, "players": {}})()
    assert [name for _, _, name, _ in lobby.items(menu, "Alex")] == ["Player 1", "Player 2"]


def test_the_menu_still_refuses_a_taken_player():
    g, _ = make_game([1, 1])
    g.sides = {"Alex": 1}
    assert not g.choose("Steve", 1)


@pytest.mark.parametrize("value", ["1,3", "2", "0,1", "1,x", ""])
def test_a_seat_list_with_a_gap_is_an_error(value):
    with pytest.raises(SystemExit):
        run.seat_list(value)


def test_the_recap_and_the_score_name_player_1_once():
    _, g, _ = scenario_game({"0": {}, "1": {}})
    g.bots = []
    g.game = type("G", (), {"sides": {"Alex": 1, "Steve": 1}})()
    assert list(score.points(g)) == [1]
    pages = recap.parts(g, lambda n: True)
    recap_page, score_page = pages[0][1], pages[1][1]
    assert recap_page.count("Player 1") == 1 and score_page.count("Player 1") == 1
    assert [t for t, _ in pages].count("Player 1") == 1
