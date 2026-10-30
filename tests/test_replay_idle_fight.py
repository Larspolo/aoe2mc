"""Live replay: a villager that attacks an enemy unit is not idle while the enemy lives (#4063). The record has no
deaths, so the last record command of the enemy is the earliest end of the fight."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_eco import vill  # noqa: E402


def fight(scout_moves, next_order=100_000):
    """The idle seconds of villager 1 that attacks the scout 5 of player 2 at 10 s, up to its next command."""
    timeline = [dict(time=10_000, player=1, kind="order", objects=[1], target=5, tile=[2.0, 2.0]),
                *(dict(time=t, player=2, kind="move", objects=[5], tile=[3.0, 3.0]) for t in scout_moves),
                dict(time=next_order, player=1, kind="move", objects=[1], tile=[1.0, 1.0])]
    r = replay.Replay(Fake(), data(timeline), ai=True)
    r.grid()
    v = vill(r, "VILLAGER_MALE", 1, 1)
    scout = vill(r, "SCOUT_CAVALRY", 2, 5)
    v.pos, scout.pos = (4.5, 70.0, 4.5), (8.5, 70.0, 8.5)
    r.idle_time(0)
    r.commands(timeline[0])
    for t in range(10_000, next_order + 1, 10_000):
        r.idle_time(t)
    return r.idled[1]


def test_a_villager_is_busy_while_its_enemy_gets_commands():
    assert fight([30_000, 60_000]) == 10 + 40                  # idle before the order and after the last scout move


def test_an_enemy_with_no_later_command_ends_the_fight_at_once():
    assert fight([]) == 100


def test_a_new_order_ends_the_fight():
    r = replay.Replay(Fake(), data([]), ai=True)
    r.fighting[1] = 90_000
    r.commands(dict(time=20_000, player=1, kind="stop", objects=[1]))
    assert 1 not in r.fighting
