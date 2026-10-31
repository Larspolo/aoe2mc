"""game/fleet.py and game/build.py: a fishing ship builds a fish trap on the water and gathers its food (#1438). Fake
server, no Minecraft (but the server test of the blocks)."""
import shutil

import pytest
from test_lang_orders import plain_log
from test_ship_gather import fish_map, play

from game import build, fleet, gather, run

TRAP = (17, 20, 5, 8)                                                  # block footprint (x0, x1, z0, z1): open water
WOOD = 300 - build.COSTS["FISH_TRAP"]["wood"]                          # the wood after the trap is placed


def feudal():
    server, g, uuid = fish_map()
    g.techs.add("FEUDAL_AGE")
    g.stock["wood"] = 300
    return server, g, uuid


def built(g, uuid):
    """Found the fish trap TRAP and let the fishing ship uuid build it to the end. Returns the site."""
    site = build.found(g, "FISH_TRAP", TRAP)
    assert fleet.build_site(g, {uuid}, site) == {uuid}
    for _ in range(800):
        if site["progress"] >= 1:
            break
        g.step()
    return site


def test_a_fish_trap_stands_on_free_water_only():
    server, g, uuid = feudal()
    assert build.water(g, TRAP)                                       # the open water: no land needed
    assert build.water(g, (14, 17, 5, 8))                             # next to the shore
    assert not build.water(g, (12, 15, 5, 8))                         # 2 columns on land
    assert not build.water(g, (14, 17, 11, 14))                       # on the dock
    assert not build.water(g, (22, 25, 5, 8))                         # out of the map


def test_the_look_at_the_water_places_the_trap_and_the_selected_ship_builds_it():
    server, g, uuid = feudal()
    server.chosen = build.MENU.index("FISH_TRAP") + 1
    g.select(uuid)
    eye = (12.5, 65.62, 6.5)
    d = next(gather.direction(-90, p / 2) for p in range(2, 80) if fleet.pick(g, eye, gather.direction(-90, p / 2)) == (18, 6))
    site = build.place(g, "Steve", "FISH_TRAP", eye, d)
    assert site and site["footprint"] == TRAP and g.stock["wood"] == WOOD and site["commands"]
    assert all(int(c.split()[2]) <= 64 for c in site["commands"] if c.startswith("fill"))   # on the water, no tower
    assert build.place(g, "Steve", "FISH_TRAP", (8.5, 65.62, 6.5), gather.direction(-90, 40)) is None   # land
    assert any("A fish trap must stand on the water." in c for c in plain_log(server.log))
    v = g.ships[uuid]
    d2 = next(gather.direction(-90, p / 2) for p in range(2, 80) if fleet.pick(g, eye, gather.direction(-90, p / 2)) == (19, 6))
    assert fleet.build_order(g, "Steve", eye, d2)                      # a click at the site: back to work
    cells = {(x, z) for x in range(17, 20) for z in range(5, 8)}
    assert v.site is site and v.state == "to_site" and v.path[-1] in g.map.around(cells, water=True)


def test_the_ship_builds_in_the_build_time_and_then_fishes_the_trap():
    server, g, uuid = feudal()
    v = g.ships[uuid]
    site = build.found(g, "FISH_TRAP", TRAP)
    assert g.stock["wood"] == WOOD
    fleet.build_site(g, {uuid}, site)
    play(g, 10)                                                         # it sails next to the trap
    assert v.state == "build"
    t = 0
    while site["progress"] < 1:
        g.step()
        t += g.tick * gather.NORMAL
    assert abs(t - build.BUILD_TIMES["FISH_TRAP"]) <= 1                  # one builder: the AoE2 build time
    tile = fleet.trap(g, site)
    assert tile == (18, 6) and g.map.fish[tile] == gather.TRAP_FOOD and g.map.traps[tile] == {
        (x, z) for x in range(17, 20) for z in range(5, 8)}
    assert v.site is None and v.tree == tile and v.state in ("to_tree", "chop")


def test_the_ship_gathers_the_trap_at_the_aoe2_rate_and_drops_at_the_dock():
    server, g, uuid = feudal()
    v, food = g.ships[uuid], g.stock["food"]
    tile = fleet.trap(g, built(g, uuid))
    play(g, 5)
    assert v.state == "chop" and v.cell in fleet.spots(g, tile)
    load = v.load
    play(g, 20)                                                         # the trap rate per game second
    assert abs(v.load - load - gather.SHIP_WORK["trap"] * 20) <= 1
    for _ in range(400):
        fleet.tick(g, 0.25)
        if g.stock["food"] > food:
            break
    n = fleet.carry(g)
    assert g.stock["food"] == food + n and g.map.fish[tile] == gather.TRAP_FOOD - n - v.load
    play(g, 20)
    assert v.tree == tile                                               # back to its trap


def test_an_empty_trap_stops_its_ship_and_no_ship_takes_a_trap_as_the_next_fish():
    server, g, uuid = feudal()
    v, food = g.ships[uuid], g.stock["food"]
    tile = fleet.trap(g, built(g, uuid))
    g.map.fish[tile] = 4
    play(g, 80)
    assert g.stock["food"] == food + 4 and v.state == "idle" and v.tree is None   # not the salmon next to it
    assert g.map.fish[tile] == 0 and tile in g.map.traps
    assert fleet.nearest(g, (18, 7)) == (20, 12)                       # a fish, not the trap


@pytest.mark.mc
def test_the_blocks_of_a_fish_trap_site_are_valid_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    server, g, uuid = feudal()
    site = build.found(g, "FISH_TRAP", TRAP)
    with run.Game(world) as game:
        game.command("forceload add 0 0 31 31")
        out = [game.command(c) for c in site["commands"]]
        assert out and all(o.startswith(("Changed the block", "Successfully filled", "No blocks were filled", "Could not set"))
                           for o in out), out
        assert "Test passed" in game.command("execute if block 18 64 6 minecraft:dark_oak_wood[axis=x]")
