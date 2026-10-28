"""Live replay on Paper: a unit with a walk order whose Minecraft path has a step that it cannot take gets free (#2304).
In de-64.3 two villagers stood for minutes at (337.3, 276.5) with an order: the next column has a moss carpet (1/16
block), and the step onto it lifts the head of the villager (1.95 blocks) into the leaves 2 blocks over its own column.
The replay sends the unit with /tp to the start of its leg (Replay.unstick). Fake RCON."""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay_catch_up import Entity, walk  # noqa: E402


class Stuck(Entity):
    """The entity of u1 stands still at `at` until a /tp moves it; then it walks with each order."""
    def command(self, cmd):
        if m := re.match(r"tp u1 (\S+) \S+ (\S+)$", cmd):
            self.at = None                                         # free: it walks its legs again
            self.leg = float(m[1]), float(m[2])
        return super().command(cmd)


def test_a_unit_that_cannot_walk_gets_free():
    game = Stuck(at=(30.5, 42.5))                                  # held on its first leg, far from its leg ends
    walk(game)
    tps = [c for c in game.sent if c.startswith("tp u1 ")]
    assert len(tps) == 1                                           # once: after the /tp it walks
    i = game.sent.index(tps[0])
    assert game.sent[i + 2].startswith("aoe moveto u1 ")           # then the next leg from there
    x, z = map(float, re.match(r"tp u1 (\S+) \S+ (\S+)$", tps[0]).groups())
    assert (x, z) != (30.5, 42.5) and (x - 0.5) % 1 == 0 and (z - 0.5) % 1 == 0   # the middle of a path cell


def test_a_walking_unit_gets_no_tp():
    game = Entity()                                                # always at the start of its leg: it walks
    walk(game)
    assert not [c for c in game.sent if c.startswith("tp u1 ")]


def test_a_unit_waits_still_ms_before_the_tp():
    r = replay.Replay(Entity(at=(30.5, 42.5)), {"map_size": 16, "tile_size": 4, "objects": [], "timeline": [],
                                                "players": {}, "ground": ["70"] * 64}, ai=True)
    v = type("V", (), {"uuid": "u1"})()
    start = (10.5, 70.0, 42.5)
    assert r.unstick(v, start, 0, (30.5, 42.5)) == []              # the first look: no place before
    assert r.unstick(v, start, replay.STILL - 1, (30.5, 42.5)) == []   # too soon
    assert r.unstick(v, start, replay.STILL, (30.5, 42.5)) == []   # the place of the look before was at STILL - 1
    assert r.unstick(v, start, 2 * replay.STILL, (30.5, 42.5)) == ["tp u1 10.5 70.0 42.5"]
    assert r.unstick(v, start, 9 * replay.STILL, (11.5, 42.5)) == []   # at its leg start: not stuck
