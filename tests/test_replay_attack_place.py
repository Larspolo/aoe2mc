"""#3540: the replay position of a unit that attacks a unit of the record follows its target after the leg to the
order tile. In de-63.0 the scout cavalry 15318 chased a villager 100 to 160 blocks from the order tile, and the drift
tool counted it as stuck. A new order starts at the place of the chase. Fake RCON on Paper."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay_ai import MIL, play  # noqa: E402
from test_replay_attack import ENEMY  # noqa: E402
from test_replay_walk import HOUSE  # noqa: E402

N = 128                                                             # 32 × 32 tiles
ORDER = dict(time=0, player=1, kind="order", objects=[8], names=["MILITIA"], target=20, tile=[12.5, 10.5])
FLEE = dict(time=1000, player=2, kind="move", objects=[20], names=["ARCHER"], tile=[24.5, 24.5])


def test_the_attacker_is_at_the_replay_position_of_its_target():
    r, _, _ = play([ORDER, FLEE], (MIL, HOUSE, ENEMY), n=N)
    v, w = r.units[8], r.units[20]
    t = max(v.leg[2], (getattr(w, "leg", None) or (0, 0, 0))[2]) + 1000
    assert math.dist(replay.Replay.at(r, v, t)[::2], w.pos[::2]) < 1     # (98.5, 98.5), not the order tile (50.5, 42.5)
    assert math.dist(replay.Replay.at(r, v, t)[::2], (50.5, 42.5)) > 40


def test_a_new_move_starts_at_the_place_of_the_chase():
    move = dict(time=120000, player=1, kind="move", objects=[8], names=["MILITIA"], tile=[24.5, 20.5])
    r, _, _ = play([ORDER, FLEE, move], (MIL, HOUSE, ENEMY), n=N)
    v = r.units[8]
    assert getattr(v, "hunt", None) is None
    assert math.dist(v.leg[0][::2], r.units[20].pos[::2]) < 1 and v.leg[1] == 120000     # not from the order tile


def test_two_units_that_attack_each_other_do_not_loop():
    r, _, _ = play([ORDER], (MIL, HOUSE, ENEMY), n=N)
    r.units[20].hunt = 8
    assert replay.Replay.at(r, r.units[8], 10 ** 9) == r.units[8].pos            # one step only: no recursion
