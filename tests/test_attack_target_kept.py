"""#3636: in de-63.0 the scout cavalry 15318 got an ORDER on villager 28728 with a tile 9 tiles from the villager's
replay place, but the scout stood 2.5 tiles from the villager. far() made it a walk to the tile, and there its sight
took another enemy. A target near a unit of the order is an attack target, also when it is far from the tile."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay_ai import MIL, play  # noqa: E402
from test_replay_attack import ENEMY, attacks  # noqa: E402
from test_replay_walk import HOUSE  # noqa: E402

N = 128                                                             # 32 × 32 tiles


def test_a_target_near_the_attacker_is_attacked_also_far_from_the_tile():
    near = dict(MIL, tile=[10.5, 10.5])                                     # 2 tiles west of the enemy
    tile = [12.5, 10.5 + replay.FAR + 1]                                    # the tile: FAR + 1 tiles south of it
    order = dict(time=0, player=1, kind="order", objects=[8], names=["MILITIA"], target=20, tile=tile)
    _, sent, _ = play([order], (near, HOUSE, ENEMY), n=N)
    assert attacks(sent) == ["aoe attack u2 e1"]
