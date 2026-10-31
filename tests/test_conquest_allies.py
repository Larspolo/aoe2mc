"""game/conquest.py: allied players win together, as the AoE2 conquest (#1313)."""
from test_cheat_end import game
from test_conquest import check, live


def setup():
    """Players 1 and 2 on team 1, player 3 alone; all three have units."""
    server, g = game()
    g.players = {"0": {}, "1": {"team": 1}, "2": {"team": 1}, "3": {}}
    live(server, {1, 2, 3})
    check(g)
    return server, g


def test_the_allies_win_when_the_other_team_is_defeated():
    server, g = setup()
    live(server, {1, 2})
    check(g)
    assert g.defeated == {3} and g.ended == "Victory"
    assert 'title @a[team=p1] title {"translate":"aoe2mc.victory","fallback":"Victory","color":"gold"}' in server.log


def test_a_defeated_ally_does_not_end_the_game():
    server, g = setup()
    live(server, {1, 3})
    check(g)
    assert g.defeated == {2} and not g.ended
    live(server, {1})
    check(g)
    assert g.ended == "Victory"
