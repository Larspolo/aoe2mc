"""game/build.py: a line of palisade or stone wall with two clicks (#1322). Fake server, no Minecraft."""
import math

from test_build_site import site_map
from test_lang_orders import plain_log

from aoe2mc import wall_tiles
from game import build, combat


def wood(g):
    return build.price(g, "PALISADE_WALL")["wood"]                     # one tile


def test_the_menu_has_the_walls_and_the_age_lock():
    server, g = site_map()
    items = {name: (icon, lore) for _, icon, name, lore in build.items(g)}
    assert items["Palisade Wall"][0] != build.LOCKED
    assert items["Stone Wall"][0] == build.LOCKED and items["Stone Wall"][1].endswith("\nNeeds the Feudal Age")
    g.techs = {"FEUDAL_AGE"}
    assert dict((n, i) for _, i, n, _ in build.items(g))["Stone Wall"] != build.LOCKED


def test_two_clicks_make_a_line_of_sites_and_take_the_cost_of_each_tile():
    server, g = site_map(wood=200, chosen=build.MENU.index("PALISADE_WALL") + 1)
    assert build.wall(g, "Steve", "PALISADE_WALL", (8, 10)) is None and not g.sites     # the first click: the start
    assert any("right click the end of the wall" in c for c in plain_log(server.log)) and server.chosen
    first = build.wall(g, "Steve", "PALISADE_WALL", (12, 14))
    tiles = wall_tiles(8, 10, 12, 14)
    assert first is g.sites[0] and [s["footprint"][::2] for s in g.sites] == tiles and len(tiles) == 5
    assert all(s["name"] == "PALISADE_WALL" and s["line"] == g.sites[0]["footprint"] for s in g.sites)
    assert g.stock["wood"] == 200 - wood(g) * 5 and server.chosen == 0
    assert not any(g.map.free(x, z) for x, z in tiles)


def test_a_click_on_the_start_tile_makes_one_tile():
    server, g = site_map()
    build.wall(g, "Steve", "PALISADE_WALL", (8, 10))
    build.wall(g, "Steve", "PALISADE_WALL", (8, 10))
    assert [s["footprint"] for s in g.sites] == [(8, 9, 10, 11)] and g.stock["wood"] == 200 - wood(g)


def test_the_tiles_on_a_building_tree_or_water_are_left_out_and_not_paid():
    server, g = site_map()
    build.wall(g, "Steve", "PALISADE_WALL", (0, 3))                    # through the town center (blocks 2..4)
    build.wall(g, "Steve", "PALISADE_WALL", (8, 3))
    assert [s["footprint"][0] for s in g.sites] == [0, 1, 5, 6, 7, 8] and g.stock["wood"] == 200 - wood(g) * 6
    build.wall(g, "Steve", "PALISADE_WALL", (18, 5))                   # over the water at x = 20
    build.wall(g, "Steve", "PALISADE_WALL", (22, 5))
    assert [s["footprint"][0] for s in g.sites[6:]] == [18, 19, 21, 22]


def test_no_line_without_the_resources_or_the_age():
    server, g = site_map()
    cost = 5 * wood(g)
    g.stock["wood"] = cost - 1
    build.wall(g, "Steve", "PALISADE_WALL", (8, 10))
    build.wall(g, "Steve", "PALISADE_WALL", (8, 14))                  # 5 tiles
    assert not g.sites and g.stock["wood"] == cost - 1
    assert any(f"5 tiles of palisade wall cost {cost} wood" in c for c in plain_log(server.log))
    server, g = site_map()
    eye, d = (8.5, 65.62, 12.5), (1.0, -0.5, 0.0)
    assert build.place(g, "Steve", "STONE_WALL", eye, d) is None and not vars(g).get("wall_start")
    assert any("Stone Wall: Needs the Feudal Age" in c for c in plain_log(server.log))


def test_the_builders_go_on_to_the_next_tile_and_a_done_tile_has_the_aoe2_hit_points():
    server, g = site_map()
    build.wall(g, "Steve", "PALISADE_WALL", (8, 10))
    build.wall(g, "Steve", "PALISADE_WALL", (8, 13))
    a, b, c, d = g.sites
    assert build.next_tile(g, b) is a                                   # the nearest unfinished tile first
    assert build.rise(g, b, math.inf)
    uuid = combat.target_uuid([8, 11, 9, 12])
    s = combat.wall("PALISADE_WALL", 0)                                 # the Dark Age hit points
    assert any(cmd.startswith(f"aoe building {uuid} {s.hp} {s.melee} {s.pierce} ") for cmd in server.log)
    assert f"tag {uuid} add aoe2mc.wall" in server.log
    build.rise(g, a, math.inf)
    assert build.next_tile(g, a) is c and build.next_tile(g, b) is c
    g.techs = {"FEUDAL_AGE"}
    build.rise(g, c, math.inf)
    s = combat.wall("PALISADE_WALL", 1)
    assert any(cmd.startswith(f"aoe building {combat.target_uuid([8, 12, 9, 13])} {s.hp} {s.melee} {s.pierce} ") for cmd in server.log)
    build.rise(g, d, math.inf)
    assert build.next_tile(g, d) is None
    house = build.found(g, "HOUSE", (14, 16, 14, 16))
    assert build.next_tile(g, house) is None                            # a building of no line
