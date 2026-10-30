"""The end of a game of two people (#1936): the team of each person gets its own "Victory" or "Defeat" title."""
import types

from test_cheat_end import game
from test_conquest import check, live

from game import gather, relic_victory, run, wonder


def title(n, text):
    return f'title @a[team=p{n}] title {{"text":"{text}","color":"{"gold" if text == "Victory" else "red"}"}}'


def two():
    """Player 1 steps the Side of player 2 (run.play); player 2 sees player 1 through peers."""
    server, g1 = game()
    g1.players = {str(p): {"color": "blue"} for p in (0, 1, 2, 3)}
    g2 = gather.Gather.__new__(gather.Gather)
    g2.player, g2.players, g2.peers, g2.command = 2, g1.players, [g1], server.command
    g2.sites, g2.queues = [], {}
    g1.bots = [run.Side(g2)]
    return server, g1, g2


def ends(server, g1, g2, win, lose):
    assert title(win, "Victory") in server.log and title(lose, "Defeat") in server.log
    assert {g1.player: g1.ended, g2.player: g2.ended} == {win: "Victory", lose: "Defeat"}


def conquest(alive):
    server, g1, g2 = two()
    live(server, {1, 2})
    check(g1)
    assert not g1.ended and not g2.ended
    live(server, alive)
    server.log.clear()
    check(g1)
    return server, g1, g2


def test_player_2_with_nothing_left_loses_and_player_1_wins():
    ends(*conquest({1}), win=1, lose=2)


def test_player_1_with_nothing_left_loses_and_player_2_wins():
    ends(*conquest({2}), win=2, lose=1)


def test_a_wonder_of_player_2_wins_for_team_p2():
    server, g1, g2 = two()
    g1.wonders, g1.wonder_at = {"w": {"player": 2, "left": 1.0}}, g1.clock() + 1e9
    wonder.tick(g1, 2.0)
    ends(server, g1, g2, win=2, lose=1)


def test_all_relics_of_player_2_win_for_team_p2(monkeypatch):
    server, g1, g2 = two()
    monkeypatch.setattr(relic_victory, "holder", lambda g: 2)
    g1.relic_timer = {"player": 2, "left": 1.0, "shown": None}
    relic_victory.tick(g1, 2.0)
    ends(server, g1, g2, win=2, lose=1)


def test_a_wonder_of_an_enemy_bot_defeats_both_people_and_the_bot_gets_no_title():
    server, g1, g2 = two()
    b = gather.Gather.__new__(gather.Gather)
    b.player, b.share = 3, g1
    g1.bots = [*g1.bots, types.SimpleNamespace(g=b)]
    g1.wonders, g1.wonder_at = {"w": {"player": 3, "left": 1.0}}, g1.clock() + 1e9
    wonder.tick(g1, 2.0)
    assert title(1, "Defeat") in server.log and title(2, "Defeat") in server.log
    assert not any("team=p3" in c for c in server.log if c.startswith("title"))
    assert (g1.ended, g2.ended, b.ended) == ("Defeat", "Defeat", "Victory")
