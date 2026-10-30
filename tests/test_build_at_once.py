"""game/gather.py: the selected villagers build a placed building, wall line or gate at once, as in AoE2 (#1654).
Fake server, no Minecraft."""
import contextlib
import io
import json
import time

import pytest
from test_build_rise import DOWN
from test_build_site import Server
from test_gather import grid

from game import build, gather, run


def line_map(villagers=2):
    """A flat 48 × 48 block map (tile size 4), wood, two selected villagers near the block (30, 30), no site yet."""
    data = grid([[64] * 48 for _ in range(48)])
    data.update(tile_size=4, level_height=1, players={"1": {"civ": "BRITONS", "color": "blue", "arch": "western"}})
    ents = {"Steve": {"Pos": (9.5, 64.0, 9.5), "Rotation": DOWN}}
    for i in range(villagers):
        data["objects"].append({"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": f"v{i}"})
        ents[f"v{i}"] = {"Pos": (30.5 + i, 64.0, 30.5)}
    server = Server(ents)
    g = gather.Gather(server, data, start={}).setup()
    g.stock["wood"] = 200
    g.selected = set(g.villagers)                                      # a box selection
    return server, g


def click(server, g, name, x):
    """Choose name in the build menu and click the ground under the block (x, 9)."""
    server.chosen = build.MENU.index(name) + 1
    server.entities["Steve"]["Pos"] = (x + 0.5, 64.0, 9.5)
    g.click("Steve")


def test_the_selected_villagers_build_a_wall_line_tile_by_tile_and_then_a_gate():
    server, g = line_map()
    click(server, g, "PALISADE_WALL", 9)                               # the start: tile (2, 2)
    assert not g.sites and all(v.state == "idle" for v in g.villagers.values())
    click(server, g, "PALISADE_WALL", 21)                              # the end: tile (5, 2)
    assert [s["footprint"][0] for s in g.sites] == [8, 12, 16, 20]
    first = g.sites[0]
    assert all(v.site is first and v.state == "to_site" for v in g.villagers.values())   # the first tile of the line
    for _ in range(3000):
        g.step()
        if all(s["progress"] >= 1 for s in g.sites) and all(v.state == "idle" for v in g.villagers.values()):
            break
    assert all(s["progress"] >= 1 for s in g.sites)                    # one tile after the other, with no new click
    click(server, g, "PALISADE_GATE", 13)
    gate = g.sites[-1]
    assert gate["name"] == "PALISADE_GATE" and gate["footprint"] == (8, 24, 8, 12)
    assert all(v.site is gate and v.state == "to_site" for v in g.villagers.values())


def test_the_selected_villagers_build_a_house_and_no_villager_goes_without_a_selection():
    server, g = line_map()
    click(server, g, "HOUSE", 9)
    house, = g.sites
    assert all(v.site is house and v.state == "to_site" for v in g.villagers.values())
    server, g = line_map()
    g.selected.clear()
    click(server, g, "HOUSE", 9)
    assert g.sites and all(v.site is None and v.state == "idle" for v in g.villagers.values())


class Clicks:
    """A real server with one fake player "Steve": his place, look and build menu choice; all other commands go to
    the server, so the villagers walk and build there."""

    def __init__(self, game):
        self.game, self.at, self.chosen = game, (0.0, 0.0, 0.0), 0

    def __getattr__(self, name):
        return getattr(self.game, name)

    def command(self, cmd):
        if cmd == "data get entity Steve Pos":
            return "Steve has the following entity data: [{}d, {}d, {}d]".format(*self.at)
        if cmd == "data get entity Steve Rotation":
            return "Steve has the following entity data: [{}f, {}f]".format(*DOWN)
        if cmd == f"scoreboard players get Steve {build.OBJECTIVE}":
            return f"Steve has {self.chosen} [{build.OBJECTIVE}]"
        if cmd == f"scoreboard players set Steve {build.OBJECTIVE} 0":
            self.chosen = 0
        return self.game.command(cmd)


@pytest.mark.mc
def test_the_selected_villagers_build_a_wall_line_and_a_gate_on_a_server(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
    scn = scenarios.new_scenario(16)
    um = scn.unit_manager
    um.add_unit(scenarios.PlayerId.ONE, BuildingInfo.TOWN_CENTER.ID, x=4, y=4)
    for x in (8.5, 9.5):
        um.add_unit(scenarios.PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=x, y=8.5)
    src = str(tmp_path / "wall.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        server = Clicks(game)
        end = time.time() + 60                                         # entities load in other threads
        while True:
            g = gather.Gather(server, data, tick=0.25, start={}).setup()
            if len(g.villagers) == 2:
                break
            assert time.time() < end, "the villagers did not load"
            time.sleep(1)
        g.stock["wood"] = 200
        g.selected = set(g.villagers)

        def click(name, tx, tz=12):
            x, z = tx * 4 + 2, tz * 4 + 2
            server.at, server.chosen = (x + 0.5, g.map.y(x, z) + 10, z + 0.5), build.MENU.index(name) + 1
            g.click("Steve")

        click("PALISADE_WALL", 9)
        click("PALISADE_WALL", 12)                                     # 4 tiles: (9, 12) to (12, 12)
        assert [s["footprint"][0] for s in g.sites] == [36, 40, 44, 48]
        assert all(v.site is g.sites[0] for v in g.villagers.values())
        end = time.time() + 120
        while not all(s["progress"] >= 1 for s in g.sites) or any(v.state != "idle" for v in g.villagers.values()):
            assert time.time() < end, "the wall line is not complete after 120 s"
            g.step()
        click("PALISADE_GATE", 10)
        gate = g.sites[-1]
        assert gate["footprint"] == (36, 52, 48, 52) and all(v.site is gate for v in g.villagers.values())
        end = time.time() + 120
        while gate["progress"] < 1:
            assert time.time() < end, "the gate is not complete after 120 s"
            g.step()
