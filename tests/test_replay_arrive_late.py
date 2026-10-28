"""Live replay on Paper: a villager whose plugin walk to its resource ends far from it ("no path") gets a new walk
order, then a /tp, well before LATE (#2709: villager 9932 of de-64.3 stood 50 to 60 s 9 blocks from its tree)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_gather import TREE, VIL, order  # noqa: E402


class Entity(Fake):
    """The entity stands at (0.5, 0.5), or walks `step` blocks along x at each position check. `sent` gets the number
    of position checks next to each command (one check each WAIT of game time)."""
    def __init__(self, step=0.0):
        super().__init__()
        self.step, self.checks, self.at = step, 0, []

    def command(self, cmd):
        super().command(cmd)
        self.at.append((self.checks, cmd))
        if cmd.startswith("data get entity u1 Pos"):
            self.checks += 1
            return f"Villager has the following entity data: [{0.5 + self.step * self.checks}d, 70.0d, 0.5d]"
        return ""


def play(game, end=90000):
    d = data([order(0, 20), dict(time=end, player=1, kind="chat", text="end")])
    d["objects"] += [VIL, TREE]
    now = [0.0]

    def sleep(s):
        now[0] += s
    r = replay.Replay(game, d, ai=True)
    r.run(clock=lambda: now[0], sleep=sleep, log=None)
    return r


def test_a_villager_that_stands_far_from_its_tree_walks_again_then_goes_there_with_tp():
    game = Entity()
    r = play(game)
    pos = r.units[7].pos
    moveto, tp = "aoe moveto u1 {} {} {}".format(*pos), "tp u1 {} {} {}".format(*pos)
    again = [k for k, c in game.at if c == moveto and k > 0]           # after the first check: a new walk order
    tps = [k for k, c in game.at if c == tp]
    assert again and tps and again[0] < tps[0] < 30 * replay.WAIT / 1000, (again, tps)
    assert 7 not in r.arriving


def test_a_villager_that_still_walks_waits_until_late():
    game = Entity(step=0.6)                                             # it moves at each check: no "no path"
    r = play(game)
    pos = r.units[7].pos
    tps = [k for k, c in game.at if c == "tp u1 {} {} {}".format(*pos)]
    assert not [k for k, c in game.at if c == "aoe moveto u1 {} {} {}".format(*pos) and k > 0]
    assert tps and 50 < tps[0] < 70, tps                                # one check each WAIT until LATE
