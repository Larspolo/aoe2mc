"""Live replay on Paper: the plugin walks the units of MOVE and ORDER on a Minecraft path (#438). Fake RCON."""
import os
import re
import sys

import aoe2mc

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import ai  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_walk import HOUSE, VIL  # noqa: E402

MIL = dict(VIL, name="MILITIA", uuid="u2", ref=8, tile=[3.5, 10.5])


def play(timeline, objects=(VIL, HOUSE), speed=4.0, n=64):
    d = data(timeline, n=n)
    d["objects"] += list(objects)
    now, game = [0.0], Fake()

    def sleep(s):
        now[0] += s
    r = replay.Replay(game, d, ai=True)
    stats = r.run(speed, clock=lambda: now[0], sleep=sleep, log=None, finish=True)
    return r, [c for c in game.sent if replay.GRAPH not in c and replay.ECO not in c and replay.ARMY not in c and replay.ORDER not in c], stats  # graphs (#3448, #3756), army (#3696), build order (#4049)


def orders(sent):
    return {m[1]: tuple(float(v) for v in m.groups()[1:]) for c in sent
            if (m := re.match(r"aoe moveto (\S+) (\S+) (\S+) (\S+)$", c))}


def test_a_move_is_one_plugin_order_with_the_walk_speed():
    r, sent, _ = play([dict(time=1000, player=1, kind="move", objects=[7], tile=[10.5, 10.5], names=["VILLAGER_MALE"])])
    assert sent == [ai.speed_command("u1", "VILLAGER_MALE", 4, 4.0 * replay.PATH), "aoe moveto u1 42.5 70.0 42.5",
                    "data get entity u1 Pos"]                           # is it there (Replay.settle, #2633)
    assert not any(c.startswith("tp ") for c in sent) and not r.moving
    assert r.units[7].pos == (42.5, 70.0, 42.5)                          # the replay takes the unit at its goal
    assert ai.walk_speed("VILLAGER_MALE", 4, 4.0) == 4 * ai.walk_speed("VILLAGER_MALE", 4, 1.0)   # 4 times the game speed


def test_a_group_goes_to_the_cells_of_its_formation():
    r, sent, _ = play([dict(time=0, player=1, kind="move", objects=[7, 8], tile=[10.5, 10.5])], (VIL, MIL, HOUSE))
    goals = orders(sent)
    assert set(goals) == {"u1", "u2"} and goals["u1"] != goals["u2"]
    assert all(r.map.free(int(x), int(z)) for x, _, z in goals.values())
    assert ai.speed_command("u2", "MILITIA", 4, 4.0 * replay.PATH) in sent


def test_an_order_goes_next_to_its_target():
    r, sent, _ = play([dict(time=0, player=1, kind="order", objects=[7], target=9, tile=[6.0, 10.0])])
    x, _, z = orders(sent)["u1"]
    assert 19 <= x <= 29 and 35 <= z <= 49 and not (20 <= x < 28 and 36 <= z < 48)


def test_an_unknown_unit_or_target_gets_no_order():
    _, sent, _ = play([dict(time=0, player=1, kind="move", objects=[99], tile=[3.5, 3.5], names=[None]),
                       dict(time=0, player=1, kind="order", objects=[7], target=12345)])
    assert not orders(sent)


def test_a_long_walk_goes_in_legs():
    """The Minecraft path search reaches about 128 blocks: the plugin gets a leg of LEG cells at a time."""
    tl = [dict(time=0, player=1, kind="move", objects=[7], tile=[35.5, 10.5])]
    r, sent, stats = play(tl, (VIL,), n=160)
    legs = [c for c in sent if c.startswith("aoe moveto")]
    assert legs == ["aoe moveto u1 58.5 70.0 42.5", "aoe moveto u1 106.5 70.0 42.5", "aoe moveto u1 142.5 70.0 42.5"]
    assert stats["lag"] < 0.1 and not r.moving and r.units[7].pos == (142.5, 70.0, 42.5)


def test_the_replay_needs_few_commands_for_walks():
    """A short walk is 2 commands, not one /tp per block: the replay keeps up at speed 4. A walk right after a walk
    also reads the entity position once (Replay.catch_up, #1168)."""
    tl = [dict(time=1000 * k, player=1, kind="move", objects=[7, 8], tile=[2.5 + 10 * (k % 2), 10.5]) for k in range(20)]
    _, sent, stats = play(tl, (VIL, MIL, HOUSE))
    reads = [c for c in sent if c.startswith("data get entity ")]
    assert len(sent) - len(reads) == 20 * 2 * 2 and len(reads) == 19 * 2 + 2 and stats["lag"] < 0.1   # + settle()


def test_without_the_plugin_the_units_walk_with_tp():
    d = data([dict(time=0, player=1, kind="move", objects=[7], tile=[10.5, 10.5])])
    d["objects"] += [VIL, HOUSE]
    game = Fake()
    replay.Replay(game, d, aoe2mc.VERSION_NAME).run(4.0, clock=lambda: 1e9, sleep=lambda s: None, log=None, finish=True)
    assert any(c.startswith("tp u1 ") for c in game.sent) and not orders(game.sent)
