"""game/build.py: villagers build a construction site layer by layer in the AoE2 build time (#418)."""
import contextlib
import io
import json
import time

import pytest
from test_build_site import Server
from test_gather import grid

from game import build, gather, run

DOWN = (0.0, 90.0)                                                     # yaw, pitch: look straight down


def rise_map(villagers=1):
    """A flat 48 × 48 block map (tile size 4), wood for a house, and villagers near the block (30, 30)."""
    data = grid([[64] * 48 for _ in range(48)])
    data.update(tile_size=4, level_height=1, players={"1": {"civ": "BRITONS", "color": "blue", "arch": "western"}})
    ents = {"Steve": {"Pos": (9.5, 64.0, 9.5), "Rotation": DOWN}}
    for i in range(villagers):
        uuid = f"v{i}"
        data["objects"].append({"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": uuid})
        ents[uuid] = {"Pos": (30.5 + i, 64.0, 30.5)}
    server = Server(ents, chosen=1)
    g = gather.Gather(server, data, start={}).setup()
    g.stock["wood"] = 100
    g.click("Steve")                                                   # a house at blocks 4..11
    return server, g


def build_with(server, g, uuids):
    site, = g.sites
    for u in uuids:
        g.select(u)
        g.click("Steve")                                               # a click on the foundation
    n, ticks = len(server.log), 0
    for _ in range(1000):
        g.step()
        ticks += any(v.state == "build" for v in g.villagers.values())
        if all(g.villagers[u].state == "idle" for u in uuids):
            break
    return site, ticks, server.log[n:]


def test_a_click_on_a_foundation_sends_a_builder():
    server, g = rise_map()
    site, = g.sites
    assert site["footprint"] == (4, 12, 4, 12) and site["commands"] and site["progress"] == 0
    g.select("v0")
    g.click("Steve")
    v = g.villagers["v0"]
    assert v.state == "to_site" and v.site is site
    assert 'data merge entity v0 {VillagerData:{profession:"minecraft:mason"},Offers:{Recipes:[]}}' in server.log
    assert v.path[-1] in g.map.around({(x, z) for x in range(4, 12) for z in range(4, 12)})


def test_the_house_rises_from_the_bottom_up_in_the_build_time():
    server, g = rise_map()
    site, ticks, log = build_with(server, g, ["v0"])
    assert site["progress"] == 1 and g.villagers["v0"].site is None
    assert ticks == pytest.approx(build.BUILD_TIMES["HOUSE"] / gather.NORMAL / g.tick, abs=1)   # AoE2 s at Normal speed
    sent, n = [c for c in log if c in site["commands"]], len(site["commands"])
    assert sent[:n] == site["commands"]                                # each command once, in order
    assert all(build.box(c)[0][:3] in site["ring"] for c in sent[n:])  # then the ring cells get their design block
    assert sent[0].startswith("fill 4 64 4 11 ") and sent[0].endswith(" air")
    ys = [int(c.split()[2]) for c in sent[1:n]]
    assert ys == sorted(ys) and ys[0] < 64 < ys[-1]
    for _ in range(20):                                                # the builder stays idle
        g.step()
    assert g.villagers["v0"].state == "idle" and not [c for c in server.log[-20:] if c.startswith("tp ")]


def test_more_builders_build_faster():
    _, ticks1, _ = build_with(*rise_map(), ["v0"])
    _, ticks2, _ = build_with(*rise_map(2), ["v0", "v1"])
    assert ticks2 == pytest.approx(ticks1 * 3 / 4, abs=2)              # AoE2: time × 3 / (n + 2)


def test_a_complete_building_takes_no_builders():
    server, g = rise_map()
    site, = g.sites
    site["progress"] = 1.0
    g.select("v0")
    g.click("Steve")
    assert g.villagers["v0"].state == "idle"


@pytest.mark.mc
def test_villager_builds_a_house_on_a_server(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import aoe2mc
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo
    scn = scenarios.new_scenario(16)
    um = scn.unit_manager
    um.add_unit(scenarios.PlayerId.ONE, BuildingInfo.TOWN_CENTER.ID, x=4, y=4)
    um.add_unit(scenarios.PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=8.5, y=8.5)
    src = str(tmp_path / "build.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        end = time.time() + 60                                         # entities load in other threads
        while True:
            g = gather.Gather(game, data, tick=0.25, start={}).setup()
            if g.villagers:
                break
            assert time.time() < end, "the villager did not load"
            time.sleep(1)
        uuid, = g.villagers
        g.stock["wood"] = 100
        x, z = 12 * 4 + 2, 10 * 4 + 2                                  # tile (12, 10): free ground
        site = build.place(g, "nobody", "HOUSE", (x + 0.5, g.map.y(x, z) + 10, z + 0.5), gather.direction(*DOWN))
        assert site and site["commands"]
        g.select(uuid)
        g.build(site)
        assert 'profession: "minecraft:mason"' in game.command(f"data get entity {uuid} VillagerData")
        end = time.time() + 120
        while g.villagers[uuid].state != "idle":
            assert time.time() < end, "the house is not complete after 120 s"
            g.step()
        assert site["progress"] == 1
        last = [c.split() for c in site["commands"] if c.startswith("setblock ")][-5:]
        for _, bx, by, bz, state in last:                              # the top blocks of the design are there
            assert "passed" in game.command(f"execute if block {bx} {by} {bz} {state}"), state
