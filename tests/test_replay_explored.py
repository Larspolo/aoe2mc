"""The explored tiles of each player grow from the start of the replay, also without a view player and around a jump,
so that a view chosen later shows all that the player saw, as in AoE2 (#1801). Fake RCON."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_minimap_fog import tiles  # noqa: E402

T = 4


def mob(uuid, player, x, y):
    return types.SimpleNamespace(uuid=uuid, player=player, name="VILLAGER_MALE", pos=(x * T + 2, 70.0, y * T + 2),
                                 cell=(x * T + 2, y * T + 2), path=[], job="none", tree=None)


def game():
    r = replay.Replay(Fake(), data([], n=128), ai=True)             # 32 x 32 tiles, no view player
    r.units = {1: mob("u1", 1, 5, 5), 2: mob("u2", 2, 25, 25)}
    return r


def test_a_view_chosen_later_shows_the_tiles_that_the_player_saw_before():
    r = game()
    start = replay.seen(r.units.values(), [], 1, T)
    assert r.fog() == []                                              # no view player: no command
    r.units[1].pos = (15 * T + 2, 70.0, 5 * T + 2)                    # 10 tiles east
    r.fog()
    r.pov = 1
    cmds = r.fog()
    now = replay.seen(r.units.values(), [], 1, T)
    assert tiles(cmds, "see") == now and tiles(cmds, "dim") == start - now
    assert (25, 25) not in r.explored[1] and (25, 25) in r.explored[2]   # each player its own sight


def test_a_jump_explores_the_start_area_the_walk_and_the_target():
    r = game()
    start = replay.seen(r.units.values(), [], 1, T)
    v = r.units[1]
    v.path, r.moving = [(22, z) for z in range(23, 83)], {1: 0}         # it walks 15 tiles south
    r.jump([], 600_000, 0)
    assert (v.pos[0] // T, v.pos[2] // T) == (5, 20)
    target = replay.seen(r.units.values(), [], 1, T)
    assert start | target <= r.explored[1] and not start & target
    assert (5, 12) in r.explored[1] and (5, 12) not in start | target   # on the walk
    r.pov = 1
    assert tiles(r.fog(), "dim") == r.explored[1] - target


def test_the_explored_tiles_outside_the_map_are_not_sent():
    r = game()
    r.units[1].pos = (0.5 * T, 70.0, 0.5 * T)
    r.fog()
    r.units[1].pos = (15 * T + 2, 70.0, 5 * T + 2)
    r.pov = 1
    assert all(0 <= x < 32 and 0 <= y < 32 for x, y in tiles(r.fog(), "dim"))
