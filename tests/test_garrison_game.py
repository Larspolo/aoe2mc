"""game/garrison.py: an order of the selected units on an own building sends them inside, the menu item "Ungarrison"
and the fall of the building let them out (#808)."""
import contextlib
import io
import json
import math
import re

import pytest
from test_gather import FakeServer, grid
from test_train_menu import menus

from game import combat, garrison, gather, train

TC = (2, 5, 2, 5)
TOWER = (10, 12, 2, 4)


class Server(FakeServer):
    """The target entities of the buildings exist until fall() removes them."""
    def __init__(self, entities):
        super().__init__(entities)
        self.targets = set()

    def command(self, cmd):
        if m := re.fullmatch(r"execute if entity ([^@\s]\S*)", cmd):
            self.log.append(cmd)
            return "Test passed" if m[1] in self.targets else "Test failed"
        return super().command(cmd)


def setup(villagers=3):
    """A flat 24 × 24 map (tile size 1): an own town center at blocks x 2-4, z 2-4 with free cells inside, an own
    watch tower at x 10-11, z 2-3, and villagers south of them. Steve looks at the town center."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5],
                "ref": 1, "inside": {"y": 65, "cells": [[3, 3], [2, 3], [4, 3]]}},
               {"kind": "building", "name": "WATCH_TOWER", "player": 1, "tile": [11.0, 3.0], "footprint": [10, 2, 12, 4],
                "ref": 2}]
    objects += [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": f"v{k}", "tile": [6.5 + k, 9.5]}
                for k in range(villagers)]
    server = Server({f"v{k}": {"Pos": (6.5 + k, 64.0, 9.5)} for k in range(villagers)} |
                    {"Steve": {"Pos": (3.5, 64.0, 9.5), "Rotation": (180, 15)}})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()
    g.paper = True
    server.targets = {combat.target_uuid(o["footprint"]) for o in objects if o["kind"] == "building"}
    return server, g


def arrive(server, g, rect):
    """The walking units stand at the door of rect; one tick lets them in."""
    x, z = garrison.door(g, rect)
    for u in g.entering:
        server.entities[u]["Pos"] = (x + 0.5, 64.0, z + 0.5)
    g.step()


def test_an_order_on_the_own_town_center_sends_the_selection_inside():
    server, g = setup()
    g.choose({"v0", "v1", "v2"}, "v0")
    now = [0.0]
    g.clock = lambda: now[0]
    server.scores["aoe_use"] = 1
    assert g.clicks() == []                                            # Paper: a stick use waits for a hold (#1786)
    now[0] = gather.HOLD
    for name in g.clicks():
        g.click(name)
    assert set(g.entering) == {"v0", "v1", "v2"} and not g.menus     # an order, not the menu
    assert all(any(c.startswith(f"aoe moveto {u} 3.5 64 5.5") for c in server.log) for u in g.entering)
    arrive(server, g, TC)
    assert g.garrisons == {TC: ["v0", "v1", "v2"]} and not g.entering and not g.selected
    for u, (x, z) in zip(["v0", "v1", "v2"], [(3, 3), (2, 3), (4, 3)]):
        assert f"tp {u} {x + 0.5} 65 {z + 0.5}" in server.log
        assert f"data merge entity {u} {garrison.INSIDE}" in server.log and f"tag {u} add aoe2mc.garrisoned" in server.log
    assert g.villagers["v0"].state == "garrison"


def test_the_menu_item_lets_the_units_out_next_to_the_door():
    server, g = setup()
    g.choose({"v0", "v1", "v2"}, "v0")
    garrison.order(g, "Steve", (3, 3))
    arrive(server, g, TC)
    train.open_menu(g, "Steve", (3, 3))
    assert " 7:oak_door:Ungarrison:Click: all units come out" in menus(server)[-1]
    server.scores["aoe_menu"] = 8                                      # slot 7
    g.clicks()
    assert not g.garrisons.get(TC) and " 7:oak_door" not in menus(server)[-1]
    ring = g.map.front(TC)
    for k, u in enumerate(["v0", "v1", "v2"]):
        x, z = ring[k]
        assert f"tp {u} {x + 0.5} 64 {z + 0.5}" in server.log and math.dist((x, z), (3, 5)) <= 2
        assert f"data merge entity {u} {garrison.OUTSIDE}" in server.log and f"tag {u} remove aoe2mc.garrisoned" in server.log
        assert g.villagers[u].state == "idle"


def test_a_menu_without_units_inside_has_no_ungarrison_item():
    server, g = setup()
    train.open_menu(g, "Steve", (3, 3))
    assert ":Ungarrison:" not in menus(server)[-1]


def test_a_fallen_building_lets_its_units_out():
    server, g = setup()
    g.choose({"v0", "v1"}, "v0")
    garrison.order(g, "Steve", (3, 3))
    arrive(server, g, TC)
    assert g.garrisons[TC] == ["v0", "v1"]
    server.targets.discard(combat.target_uuid([2, 2, 5, 5]))           # the plugin removed the target: hit points 0
    g.step()
    assert not g.garrisons.get(TC) and all(f"tag {u} remove aoe2mc.garrisoned" in server.log for u in ("v0", "v1"))


def test_a_full_watch_tower_leaves_the_last_unit_at_the_door():
    n = garrison.SIZES["WATCH_TOWER"]
    server, g = setup(villagers=n + 1)
    g.choose({f"v{k}" for k in range(n + 1)}, "v0")
    assert garrison.order(g, "Steve", (10, 2)) == TOWER
    arrive(server, g, TOWER)
    assert len(g.garrisons[TOWER]) == n
    out, = {f"v{k}" for k in range(n + 1)} - set(g.garrisons[TOWER])
    assert f"tag {out} add aoe2mc.garrisoned" not in server.log and g.villagers[out].state == "idle"
    assert out in g.selected and not g.selected - {out}


def test_units_inside_take_no_click_and_no_order():
    server, g = setup()
    g.choose({"v0"}, "v0")
    garrison.order(g, "Steve", (3, 3))
    arrive(server, g, TC)
    g.box("Steve", (0, 0))
    g.box("Steve", (23, 23))                                           # a box over the whole map
    assert g.selected == {"v1", "v2"}
    assert garrison.order(g, "Steve", (40, 40)) is None and garrison.order(g, "Steve", (8, 8)) is None


def test_a_control_group_does_not_select_the_units_inside():
    server, g = setup()
    g.choose({"v0", "v1"}, "v0")
    g.group("Steve", 1, True)
    g.choose({"v0"}, "v0")
    garrison.order(g, "Steve", (3, 3))
    arrive(server, g, TC)
    g.group("Steve", 1, False)
    assert g.selected == {"v1"} and g.groups[1] == {"v0", "v1"}


def test_the_units_of_the_converter_start_inside():
    _, g = setup()
    g.data["objects"].append({"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "w", "tile": [3.5, 3.5],
                              "holder": 1})
    assert garrison.start(g) == {TC: ["w"]}


@pytest.mark.mc
def test_garrison_on_a_server(tmp_path):
    """3 villagers walk into their town center and come out with the menu item. A watch tower takes 5 of 6 militia.
    Then 2 villagers go in again, and the town center falls to an enemy militia: they come out alive."""
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import time

    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
    from game import run
    scn = scenarios.new_scenario(24)
    um = scn.unit_manager
    um.add_unit(scenarios.PlayerId.ONE, BuildingInfo.TOWN_CENTER.ID, x=6, y=6)
    um.add_unit(scenarios.PlayerId.ONE, BuildingInfo.WATCH_TOWER.ID, x=17, y=6)
    for k in range(3):
        um.add_unit(scenarios.PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=4.5 + 2 * k, y=13.5)
    for k in range(6):
        um.add_unit(scenarios.PlayerId.ONE, UnitInfo.MILITIA.ID, x=14.5 + k, y=13.5)
    um.add_unit(scenarios.PlayerId.TWO, UnitInfo.MILITIA.ID, x=6.5, y=20.5)
    src = str(tmp_path / "g.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    tc_o = next(o for o in data["objects"] if o["name"] == "TOWN_CENTER")
    assert len(tc_o["inside"]["cells"]) >= garrison.SIZES["TOWN_CENTER"]       # the hall upstairs (#2054)
    enemy = next(o["uuid"] for o in data["objects"] if o["kind"] == "unit" and o["player"] == 2)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        combat.setup(game, data)
        g = gather.Gather(game, data, tick=0.25).setup()
        tc, = [r for r, o in garrison.holders(g).items() if o["name"] == "TOWN_CENTER"]
        tower, = [r for r, o in garrison.holders(g).items() if o["name"] == "WATCH_TOWER"]

        def walk(rect, n, seconds=40):
            end = time.time() + seconds
            while len(g.garrisons.get(rect, [])) < n or g.entering:
                assert time.time() < end, (g.entering, g.garrisons, {u: (g.pos(u), nbt(u, "Health")) for u in g.soldiers})
                g.step()
                time.sleep(g.tick)

        def nbt(u, key):
            return game.command(f"data get entity {u} {key}")
        vils = sorted(g.villagers)
        g.choose(set(vils), vils[0])
        assert garrison.order(g, "nobody", ((tc[0] + tc[1]) // 2, (tc[2] + tc[3]) // 2)) == tc
        walk(tc, 3)
        for u in vils:
            x, _, z = g.pos(u)
            assert tc[0] <= x < tc[1] and tc[2] <= z < tc[3], "inside the footprint"
            assert nbt(u, "Invulnerable").endswith("1b") and nbt(u, "NoAI").endswith("1b")
        assert not g.selected
        train.order(g, "nobody", tc, garrison.UNGARRISON[0])            # the menu item
        x, z = garrison.door(g, tc)
        for u in vils:
            p = g.pos(u)
            assert math.dist((p[0], p[2]), (x + 0.5, z + 0.5)) <= 4 and nbt(u, "Invulnerable").endswith("0b")
        import ai  # a walk order moves them again
        ai.move(g, vils[0], "VILLAGER", g.map.T, x + 0.5, g.map.y(x, z + 6), z + 6.5)
        time.sleep(4)
        assert g.pos(vils[0])[2] > z + 3, "the villager walks after the ungarrison"
        g.villagers[vils[0]].pos = g.pos(vils[0])
        militia = sorted(g.soldiers)                                   # before the enemy fights
        g.choose(set(militia), militia[0])
        garrison.order(g, "nobody", (tower[0], tower[2]))
        walk(tower, garrison.SIZES["WATCH_TOWER"])
        assert len(g.garrisons[tower]) == garrison.SIZES["WATCH_TOWER"] and len(set(militia) - set(g.garrisons[tower])) == 1
        g.choose(set(vils[1:]), vils[1])
        garrison.order(g, "nobody", (x, tc[2]))
        walk(tc, 2)
        target = combat.target_uuid([tc[0], tc[2], tc[1], tc[3]])
        game.command(f"scoreboard players set {target} aoe_hp 1")
        game.command(f"aoe attack {enemy} {target}")
        end = time.time() + 60
        while g.garrisons.get(tc):
            assert time.time() < end, "the town center does not fall"
            g.step()
            time.sleep(g.tick)
        for u in vils[1:]:
            assert "has the following entity data" in nbt(u, "Health") and g.pos(u), "alive"
            assert not tc[0] <= g.pos(u)[0] < tc[1] or not tc[2] <= g.pos(u)[2] < tc[3]
