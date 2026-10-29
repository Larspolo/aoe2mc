"""#3779 (epic #3774): "Create Garrisoned Object" and "Unload" with a transport ship or a ram as the holder. The
converter summons the unit at the holder with the tag aoe2mc.in<ref>; the game program puts it on the holder
(transport.adopt) and "Unload" lets it out on the land (transport.out)."""
import re
from collections import Counter

from test_gather import FakeServer, grid

import aoe2mc
from game import garrison, gather, scenario, transport

STORED = "Storage aoe2mc:orders has the following contents: "
UNITS = {"ship": ("TRANSPORT_SHIP", 15.5, 5.5, 7), "ram": ("BATTERING_RAM", 8.5, 12.5, 8)}


def effect(kind, ref, name="ARCHER"):
    e = dict(type=kind, player=1, object2=("U", name), selected=[ref], tile=[-1, -1], area=[-1] * 4)
    return e, aoe2mc.Effect(dict(id=0, effects=[e]), 4, None, {}, Counter(), True, {}, [])


def test_the_converter_summons_the_unit_at_the_ship_and_orders_its_unload(monkeypatch):
    monkeypatch.setattr(aoe2mc, "CARRIER_REFS", {7: "TRANSPORT_SHIP", 8: "BATTERING_RAM"})
    e, c = effect(aoe2mc.CREATE_GARRISONED_OBJECT, 7)
    line, = aoe2mc.garrisoned_lines(e, c)
    assert line.startswith("execute at @e[tag=aoe2mc.r7,limit=1] run summon ") and " ~ ~ ~ " in line
    assert f"{aoe2mc.INTO}7" in line and aoe2mc.MADE_INSIDE in line and "NoAI: 1b" in line
    assert c.stats["create garrisoned"] == 1
    e, c = effect(aoe2mc.UNLOAD, 8)
    assert aoe2mc.unload_lines(e, c) == ['data modify storage aoe2mc:orders list append value "unload 1 8"']


def test_the_carrier_names_have_the_aoe2_garrison():
    assert aoe2mc.CARRIERS == {"BATTERING_RAM": 4, "CAPPED_RAM": 5, "SIEGE_RAM": 6, "TRANSPORT_SHIP": 20}


class Server(FakeServer):
    """The unit a1 was made inside the holder `made` (its tags MADE_INSIDE and aoe2mc.in<ref>) until they go."""
    def __init__(self, entities, made):
        super().__init__(entities)
        self.made, self.order = made, None

    def command(self, cmd):
        if m := re.fullmatch(r"aoe where (\S+) (\d+)", cmd):
            self.log.append(cmd)
            if aoe2mc.MADE_INSIDE not in m[1]:
                return super().command(cmd)
            ok = self.made and (f"{aoe2mc.INTO}{self.made}," in m[1] or "aoe2mc.p1" in m[1])
            return "Where 1: a1 9.5 64.0 12.5" if ok else "Where 0: "
        if cmd == f"tag a1 remove {aoe2mc.MADE_INSIDE}":
            self.made = None
        if cmd.startswith("data get storage aoe2mc:orders"):
            self.log.append(cmd)
            return STORED + f'["{self.order}"]' if self.order else ""
        return super().command(cmd)


def setup(made):
    """A flat 24 × 24 map: land at x < 14, water at x >= 14, an own transport ship (ref 7) and ram (ref 8)."""
    objects = [{"kind": "unit", "name": n, "player": 1, "uuid": u, "ref": r, "tile": [x, z]}
               for u, (n, x, z, r) in UNITS.items()]
    server = Server({o["uuid"]: {"Pos": (o["tile"][0], 63.0 if o["tile"][0] > 14 else 64.0, o["tile"][1])}
                     for o in objects} | {"a1": {"Pos": (9.5, 64.0, 12.5)}}, made)
    g = gather.Gather(server, grid([[64] * 14 + ["-"] * 10 for _ in range(24)], objects), start={}).setup()
    g.paper = True
    return server, g


def test_a_unit_made_in_the_ship_rides_it_and_unload_lets_it_out_on_land():
    server, g = setup(7)
    garrison.adopt(g)
    garrison.adopt(g)
    assert g.cargo == {"ship": ["a1"]}                                 # once: the tag went
    assert "execute as ship on passengers run ride a1 mount @s" in server.log
    assert f"tag a1 remove {aoe2mc.INTO}7" in server.log and "aoe hide @a a1" in server.log
    server.order = "unload 1 7"
    scenario.orders(g)
    assert "ship" not in g.cargo and "ride a1 dismount" in server.log
    tp = next(c for c in server.log if c.startswith("tp a1 "))
    assert float(tp.split()[2]) < 14                                   # on the land, not on the water


def test_an_infantry_unit_made_in_the_ram_rides_it_and_comes_out():
    server, g = setup(8)
    garrison.adopt(g)
    assert g.cargo == {"ram": ["a1"]} and transport.capacity(g, "ram") == 4
    server.order = "unload 1 8 4 64 4"
    scenario.orders(g)
    assert "ram" not in g.cargo and "ride a1 dismount" in server.log
    assert server.log.index("aoe moveto a1 4 64 4") > server.log.index("ride a1 dismount")
