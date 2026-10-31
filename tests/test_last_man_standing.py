"""game/conquest.py: the AoE2 victory "Last Man Standing" (#2358, AoE2 wiki "Victory"): the allies do not win together;
when only allies are left, the alliances end, and the last player alive wins."""
from test_cheat_end import game
from test_conquest import check, live

from game import gather


def setup(victory="last-man-standing"):
    """Players 1 and 2 on team 1, player 3 alone; all three have units."""
    server, g = game()
    g.victory, g.paper = victory, True
    g.players = {"0": {}, "1": {"team": 1}, "2": {"team": 1}, "3": {}}
    live(server, {1, 2, 3})
    check(g)
    return server, g


def test_the_alliance_ends_when_only_allies_are_left():
    server, g = setup()
    live(server, {1, 2})
    check(g)
    assert g.defeated == {3} and not g.ended                       # two allies alive: no victory yet
    assert not gather.allied(g.players, 1, 2)
    assert "aoe allies -" in server.log
    assert any(c.startswith("tellraw @a") and "the alliances end" in c for c in server.log)
    check(g)
    assert not g.ended


def test_the_last_player_alive_wins():
    server, g = setup()
    live(server, {1, 2})
    check(g)
    live(server, {1})
    check(g)
    assert g.defeated == {2, 3} and g.ended == "Victory"
    assert 'title @a[team=p1] title {"text":"Victory","color":"gold"}' in server.log


def test_the_former_ally_wins_and_the_player_loses():
    server, g = setup()
    live(server, {1, 2})
    check(g)
    live(server, {2})
    check(g)
    assert g.ended == "Defeat"


def test_the_standard_victory_lets_the_allies_win_together():
    server, g = setup("standard")
    live(server, {1, 2})
    check(g)
    assert g.ended == "Victory" and gather.allied(g.players, 1, 2)
