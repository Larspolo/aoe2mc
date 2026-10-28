"""#3105, the decision #3103 (A, as AoE2): the defeat of player 1 or the resign of a person does not end the game for the
other players. The game ends when all players that are left are allies (the team wins together), or when no person is
left (only bots)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import regicide  # noqa: E402
import sudden_death  # noqa: E402
from game import cheats, gather, run  # noqa: E402

from test_cheat_end import game  # noqa: E402
from test_conquest import check, live  # noqa: E402
from test_two_players_end import title  # noqa: E402


def people(teams=None):
    """Three people: player 1 steps the Sides of players 2 and 3 (run.play); teams: {player: team}."""
    server, g1 = game()
    g1.players = {str(p): {"color": "blue"} | ({"team": teams[p]} if p in (teams or {}) else {}) for p in (0, 1, 2, 3)}
    sides = []
    for n in (2, 3):
        h = gather.Gather.__new__(gather.Gather)
        h.player, h.players, h.peers, h.command = n, g1.players, [g1], server.command
        h.sites, h.queues = [], {}
        sides.append(h)
    g1.bots = [run.Side(h) for h in sides]
    for h in sides:
        h.peers = [g1, *sides]
    return server, g1, *sides


def ended(*gathers):
    return {h.player: h.ended for h in gathers}


def test_player_1_is_out_and_the_others_play_on_until_one_is_left():
    server, g1, g2, g3 = people()
    live(server, {1, 2, 3})
    check(g1)
    live(server, {2, 3})
    server.log.clear()
    check(g1)
    assert ended(g1, g2, g3) == {1: None, 2: None, 3: None} and g1.defeated == {1}
    assert title(1, "Defeat") in server.log and "aoe destroy @e[tag=aoe2mc.building,team=p1]" in server.log
    live(server, {2})
    server.log.clear()
    check(g1)
    assert ended(g1, g2, g3) == {1: "Defeat", 2: "Victory", 3: "Defeat"} and title(2, "Victory") in server.log


def test_the_team_of_a_defeated_player_1_wins_together():
    server, g1, g2, g3 = people({1: 1, 2: 1, 3: 2})
    live(server, {1, 2, 3})
    check(g1)
    live(server, {2, 3})
    check(g1)
    assert ended(g1, g2, g3) == {1: None, 2: None, 3: None}
    live(server, {2})
    server.log.clear()
    check(g1)
    assert ended(g1, g2, g3) == {1: "Victory", 2: "Victory", 3: "Defeat"}
    assert title(1, "Victory") in server.log and title(2, "Victory") in server.log and title(3, "Defeat") in server.log


@pytest.mark.parametrize("mode", ["regicide", "sudden-death"])
def test_the_king_or_the_town_center_of_player_1_falls_and_the_game_goes_on(monkeypatch, mode):
    server, g1, g2, g3 = people()
    scored = []
    monkeypatch.setattr(regicide.conquest, "scored", lambda g, n: scored.append(n))
    monkeypatch.setattr(regicide, "has_king", lambda g, n: n != 1)
    monkeypatch.setattr(sudden_death, "has_town_center", lambda g, n: n != 1)
    g1.kings = g1.towns = {1, 2, 3}
    server.log.clear()
    (regicide if mode == "regicide" else sudden_death).tick(g1)
    assert scored == [1] and g1.defeated == {1} and title(1, "Defeat") in server.log
    assert ended(g1, g2, g3) == {1: None, 2: None, 3: None}


def test_person_2_resigns_and_players_1_and_3_play_on():
    server, g1, g2, g3 = people()
    server.log.clear()
    cheats.apply(g2, "Alex", "resign")
    assert ended(g1, g2, g3) == {1: None, 2: None, 3: None} and g1.defeated == {2}
    assert title(2, "Defeat") in server.log and "kill @e[tag=aoe2mc.p2]" in server.log


def test_the_game_ends_at_once_when_no_person_is_left():
    server, g1 = game()
    g1.players = {str(p): {"color": "blue"} for p in (0, 1, 2, 3)}
    bot = gather.Gather.__new__(gather.Gather)
    bot.player, bot.players, bot.share, bot.peers, bot.command = 2, g1.players, g1, (), server.command
    bot.sites, bot.queues = [], {}
    g1.bots = [run.Side(bot)]                                       # a bot: its Gather shares the one of player 1
    live(server, {1, 2, 3})
    check(g1)
    live(server, {2, 3})
    server.log.clear()
    check(g1)
    assert g1.ended == "Defeat" and title(1, "Defeat") in server.log
