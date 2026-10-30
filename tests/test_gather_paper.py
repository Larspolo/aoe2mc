"""Gather on Paper (#437): the villagers walk with `aoe moveto` of the plugin, not with one /tp per block."""
import math
import re

import gather
import pytest
from test_gather import FakeServer, tiny


class FakePaper(FakeServer):
    """A Paper server: `aoe moveto` sets a goal, and each position read moves the unit 1 block to it."""
    kind = "paper"

    def __init__(self, entities):
        super().__init__(entities)
        self.goals = {}

    def command(self, cmd):
        if m := re.fullmatch(r"aoe moveto (\S+) (\S+) (\S+) (\S+)", cmd):
            self.goals[m[1]] = tuple(map(float, m.groups()[1:]))
        if m := re.fullmatch(r"aoe stop (\S+)", cmd):
            self.goals.pop(m[1], None)
        if (m := re.fullmatch(r"data get entity (\S+) Pos", cmd)) and m[1] in self.goals:
            p, g = self.entities[m[1]]["Pos"], self.goals[m[1]]
            d = math.dist(p, g)
            self.entities[m[1]]["Pos"] = g if d <= 1 else tuple(a + (b - a) / d for a, b in zip(p, g))
        return super().command(cmd)


def test_villager_walks_with_the_plugin_and_stops_at_the_goal(tiny_world):
    data, uuid, _, _ = tiny(tiny_world)
    vil, = [o for o in data["objects"] if o.get("uuid") == uuid]
    m = gather.Map(data)
    x, z = int(vil["tile"][0] * 4), int(vil["tile"][1] * 4)
    server = FakePaper({uuid: {"Pos": (x + 0.5, m.y(x, z), z + 0.5)}})
    now = [0.0]
    g = gather.Gather(server, data, tick=0.25, carry=3, chop=0.25, clock=lambda: now[0]).setup()
    assert g.paper
    tree, = g.map.trees
    g.select(uuid)
    g.send(tree)
    for _ in range(400):
        g.step()
        now[0] += 0.25
    assert server.wood() >= 6                                          # at least two trips of 3 wood
    assert not any(c.startswith("tp ") for c in server.log)            # no own steps
    moves = [c for c in server.log if c.startswith("aoe moveto")]
    speed = [c for c in server.log if c.startswith(f"attribute {uuid} minecraft:movement_speed")]
    assert len(moves) >= 4 and len(speed) == len(moves)                # the AoE2 speed before each walk
    assert server.log.count(f"aoe stop {uuid}") >= len(moves) - 1      # each walk ends with a stop (the last walks)
    goals = [tuple(map(float, c.split()[3:6:2])) for c in moves]
    assert all(g.map.free(math.floor(a), math.floor(b)) for a, b in goals)
    tc = set().union(*g.map.drops["wood"])
    assert any(max(abs(math.floor(a) - p), abs(math.floor(b) - q)) == 1 for a, b in goals for p, q in tc)
    assert g.villagers[uuid].walked > 0


def test_a_villager_without_a_path_stops_after_two_orders(tiny_world):
    data, uuid, _, _ = tiny(tiny_world)
    vil, = [o for o in data["objects"] if o.get("uuid") == uuid]
    m = gather.Map(data)
    x, z = int(vil["tile"][0] * 4), int(vil["tile"][1] * 4)
    server = FakePaper({uuid: {"Pos": (x + 0.5, m.y(x, z), z + 0.5)}})
    server.goals = type("NoPath", (dict,), {"__setitem__": lambda *a: None})()   # the unit never moves
    now = [0.0]
    g = gather.Gather(server, data, tick=0.25, clock=lambda: now[0]).setup()
    tree, = g.map.trees
    g.select(uuid)
    g.send(tree)
    v = g.villagers[uuid]
    for _ in range(39):
        g.step()
        now[0] += 0.25
    assert v.state == "to_tree" and sum(c.startswith("aoe moveto") for c in server.log) == 2    # one more order
    for _ in range(3):
        g.step()
        now[0] += 0.25
    assert v.state == "idle" and f"aoe stop {uuid}" in server.log


def test_vanilla_keeps_the_own_path():
    assert not gather.Gather(FakeServer({}), {"tile_size": 4, "ground": [], "objects": []}).paper


@pytest.mark.parametrize("name", ["VILLAGER_MALE", "VILLAGER_FEMALE"])
def test_villager_speed_is_the_aoe2_speed(name):
    import ai
    assert ai.walk_speed(name, 4) == pytest.approx(ai.SPEEDS["VILLAGER"] * 4 * gather.NORMAL)   # the speed of all villagers


def test_paper_ticks_units_far_from_players():
    """Paper ticks a unit far from all players only now and then: a farmer at the far end of its farm did not walk
    back (#437). The game program turns the activation range off."""
    from game import run
    assert all(f"      {k}: 0\n" in run.SPIGOT for k in ("villagers", "monsters", "animals", "misc"))
