"""game/bot.py: a bot takes the nearest enemy still in the game when its foe is out (#4019). Fake server of
test_gather, the map of test_bot_gather."""
import types

from test_bot_attack import armed, orders, steps

TEAMS = {"1": {"team": 1}, "2": {"team": 2}, "3": {"team": 1}, "4": {"team": 2}}


def four(defeated):
    """An armed bot of player 2 with foe 1 in a game of 4 players (teams 1, 2, 1, 2), with the given players out."""
    server, me, b = armed(attack=0.0)
    b.g.players = TEAMS
    b.g.data["objects"] += [{"kind": "building", "name": "TOWN_CENTER", "player": p, "footprint": f}
                            for p, f in ((3, [26, 2, 29, 5]), (4, [26, 26, 29, 29]))]   # player 4: next to player 2
    b.share = types.SimpleNamespace(player=1, bots=[], peers=[], conquest_seen={1, 2, 3, 4}, defeated=set(defeated), sites=[],
                                    forts={}, fort_players={})
    return server, me, b


def test_the_bot_takes_the_enemy_and_never_its_ally():
    server, me, b = four({1})
    b.retarget()
    assert b.foe == 3


def test_the_foe_stays_while_it_is_in_the_game():
    server, me, b = four(set())
    b.retarget()
    assert b.foe == 1


def test_no_enemy_left_no_foe_and_no_attack():
    server, me, b = four({1, 3})
    steps(b, 5)
    assert b.foe is None and orders(server) == []
