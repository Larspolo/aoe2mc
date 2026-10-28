"""#2635: the tile of an ORDER is the place of its target in AoE2. A target unit that stands more than replay.FAR tiles
from it in the replay is no attack target: the units walk to the tile (in de-64.3 the spearman 12477 chased a
villager 200 blocks from the tile). An attacker has its replay place at the tile. Fake RCON on Paper."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay_ai import MIL, orders, play  # noqa: E402
from test_replay_attack import ENEMY, attacks  # noqa: E402
from test_replay_walk import HOUSE  # noqa: E402

N = 128                                                             # 32 × 32 tiles


def order(tile):
    return dict(time=0, player=1, kind="order", objects=[8], names=["MILITIA"], target=20, tile=tile)


def test_a_target_near_the_tile_is_attacked_and_the_replay_place_goes_there():
    r, sent, _ = play([order([12.5, 10.5])], (MIL, HOUSE, ENEMY), n=N)       # the enemy stands on the tile
    assert attacks(sent) == ["aoe attack u2 e1"] and "u2" not in orders(sent)
    v = r.units[8]
    assert v.pos[::2] == (50.5, 42.5)                                         # the tile, not the old place (14.5, 42.5)
    assert v.leg[2] - v.leg[1] > 0                                            # a leg at its walk speed
    assert replay.Replay.at(r, v, (v.leg[1] + v.leg[2]) / 2)[0] == (v.leg[0][0] + v.pos[0]) / 2


def test_a_target_far_from_the_tile_is_a_walk_to_the_tile():
    tile = [12.5 + replay.FAR + 3, 10.5]                                      # the enemy is FAR + 3 tiles west of it
    r, sent, _ = play([order(tile)], (MIL, HOUSE, ENEMY), n=N)
    assert not attacks(sent)
    assert orders(sent)["u2"][::2] == (tile[0] * 4 + 0.5, tile[1] * 4 + 0.5) and r.units[8].pos[::2] == (94.5, 42.5)


def test_an_order_without_a_tile_attacks_as_before():
    _, sent, _ = play([dict(order(None), tile=None)], (MIL, HOUSE, ENEMY), n=N)
    assert attacks(sent) == ["aoe attack u2 e1"]
