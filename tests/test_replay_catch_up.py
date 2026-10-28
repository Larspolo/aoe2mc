"""Live replay on Paper: a unit behind its replay position walks the next leg of a long walk faster (#1168). Fake RCON."""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import ai  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_walk import VIL  # noqa: E402


class Entity(Fake):
    """The entity of u1 stands at `at` (None: at the start of the leg that the last order began)."""
    def __init__(self, at=None):
        super().__init__()
        self.at, self.leg = at, (10.5, 42.5)

    def command(self, cmd):
        if cmd == "data get entity u1 Pos":
            self.sent.append(cmd)
            x, z = self.at or self.leg
            return f"u1 has the following entity data: [{x}d, 70.0d, {z}d]"
        if m := re.match(r"aoe moveto u1 (\S+) \S+ (\S+)$", cmd):
            self.leg = float(m[1]), float(m[2])                    # the next leg starts at the end of this one
        return super().command(cmd)


def walk(game):
    """A walk of about 200 blocks: 5 legs of replay.LEG cells. Returns the speed commands of the legs, in order."""
    d = data([dict(time=1000, player=1, kind="move", objects=[7], tile=[60.5, 10.5], names=["VILLAGER_MALE"])], n=256)
    d["objects"] += [VIL]
    now = [0.0]
    r = replay.Replay(game, d, ai=True)
    r.run(4.0, clock=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0] + s), log=None, finish=True)
    return [c for c in game.sent if c.startswith("attribute u1 ")]


def test_a_unit_on_time_walks_at_its_walk_speed():
    game = Entity()
    speeds = walk(game)
    assert len(speeds) >= 4 and set(speeds) == {ai.speed_command("u1", "VILLAGER_MALE", 4, 4.0 * replay.PATH)}
    assert game.sent.count("data get entity u1 Pos") == len(speeds)   # not for the first leg; at the end (settle, #2633)


def test_a_walk_right_after_a_walk_catches_up():
    """A villager with two walks in one line: the lag of the first walk goes into the second (#1168)."""
    tl = [dict(time=1000, player=1, kind="move", objects=[7], tile=[12.5, 10.5]),
          dict(time=14000, player=1, kind="move", objects=[7], tile=[22.5, 10.5]),
          dict(time=60000, player=1, kind="move", objects=[7], tile=[12.5, 10.5])]
    d = data(tl, n=128)
    d["objects"] += [VIL]
    now, game = [0.0], Entity(at=(42.5, 42.5))                     # 8 blocks before the end of the first walk
    r = replay.Replay(game, d, ai=True)
    r.run(4.0, clock=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0] + s), log=None, finish=True)
    speeds = [c for c in game.sent if c.startswith("attribute u1 ")]
    second = game.sent.index(speeds[1])
    assert game.sent[:second].count("data get entity u1 Pos") == 1   # the first walk ends right before the second
    assert speeds[0] == speeds[2] == ai.speed_command("u1", "VILLAGER_MALE", 4, 4.0 * replay.PATH)
    assert speeds[1] == ai.speed_command("u1", "VILLAGER_MALE", 4, 4.0 * replay.CATCH_UP)   # 8 blocks of lag in 16 (#1291)


class Slow(Entity):
    """The entity of u1 walks 1 block per read from the start: far behind, but not stuck (Replay.unstick, #2304)."""
    def command(self, cmd):
        if cmd == "data get entity u1 Pos":
            self.at = (self.at[0] + 1, self.at[1])
        return super().command(cmd)


def test_a_unit_behind_walks_the_next_leg_faster_up_to_the_cap():
    speeds = walk(Slow(at=(10.5, 42.5)))                            # it stays near the start: far behind
    assert speeds[0] == ai.speed_command("u1", "VILLAGER_MALE", 4, 4.0 * replay.PATH)
    assert set(speeds[1:]) == {ai.speed_command("u1", "VILLAGER_MALE", 4, 4.0 * replay.CATCH_UP)}


def test_the_factor_is_the_distance_of_the_entity_over_the_leg():
    r = replay.Replay(Entity(at=(0.5, 10.5)), data([]), ai=True)
    r.grid()                                                       # r.gather
    v = type("V", (), {"uuid": "u1", "pos": (40.5, 70.0, 10.5)})()
    assert r.catch_up(v, 32.0) == 40 / 32                           # 8 blocks behind on a leg of 32 blocks
    assert r.catch_up(v, 50.0) == 1.0                               # ahead: never slower
    assert r.catch_up(v, 0.5) == 1.0
