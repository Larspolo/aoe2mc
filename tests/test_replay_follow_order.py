"""Live replay on Paper: a FOLLOW or GUARD of the record lets the unit walk after its target, and a guarding military
unit attacks an enemy next to its target (#2551). Fake RCON."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
from test_replay_ai import MIL, play  # noqa: E402
from test_replay_attack import ENEMY, attacks  # noqa: E402
from test_replay_walk import HOUSE, VIL  # noqa: E402

FOLLOW = dict(time=0, player=1, kind="follow", objects=[8], target=7)
AWAY = dict(time=1000, player=1, kind="move", objects=[7], tile=[12.5, 10.5])   # the target walks 10 tiles
LATER = dict(time=20000, player=1, kind="chat", text="gg")             # the replay goes on until then


def walks(sent, uuid):
    """The goals (x, z) of the plugin walks of unit uuid, in order."""
    return [(float(c.split()[3]), float(c.split()[5])) for c in sent if c.startswith(f"aoe moveto {uuid} ")]


def test_a_follower_walks_after_its_target():
    r, sent, _ = play([FOLLOW, AWAY, LATER], (VIL, MIL, HOUSE))
    goal = walks(sent, "u2")[-1]
    assert math.dist(goal, (12.5 * 4, 10.5 * 4)) <= 3 * 4             # near the new place of the target
    assert r.follows[8][:2] == [7, "follow"]


def test_a_move_of_the_follower_ends_the_follow():
    stop = dict(time=500, player=1, kind="move", objects=[8], tile=[3.5, 2.5])
    r, sent, _ = play([FOLLOW, stop, AWAY, LATER], (VIL, MIL, HOUSE))
    assert len(walks(sent, "u2")) == 1 and not r.follows               # only the walk of the move


def test_a_guard_attacks_an_enemy_next_to_its_target():
    near = dict(ENEMY, tile=[2.5, 12.5])                               # 2 tiles from the villager
    guard = dict(FOLLOW, kind="guard", target_name="VILLAGER_MALE")
    _, sent, _ = play([guard, LATER], (VIL, MIL, HOUSE, near))
    assert attacks(sent) == ["aoe attack u2 e1"]


def test_a_guard_with_no_enemy_near_its_target_attacks_nothing():
    _, sent, _ = play([dict(FOLLOW, kind="guard"), LATER], (VIL, MIL, HOUSE, ENEMY))   # the enemy is 10 tiles away
    assert not attacks(sent)


def test_the_death_of_the_target_ends_the_follow():
    dead = dict(time=1000, player=1, kind="delete", objects=[7])
    r, _, _ = play([FOLLOW, dead, LATER], (VIL, MIL, HOUSE))
    assert not r.follows
