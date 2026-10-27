"""game/build.py: the player builds a wonder in the Imperial Age (#1136). Fake server, no Minecraft."""
from test_build_done import DOWN
from test_build_site import Server
from test_gather import grid

from buildings import footprint
from game import build, gather


def test_the_menu_shows_the_wonder_gray_before_the_imperial_age():
    g = gather.Gather.__new__(gather.Gather)
    g.data, g.player, g.techs = {}, 1, {"FEUDAL_AGE", "CASTLE_AGE"}
    item, = [i for i in build.items(g) if i[2] == "Wonder"]
    assert item[1] == build.LOCKED and "Needs the Imperial Age" in item[3]
    assert "1000 wood, 1000 gold, 1000 stone" in item[3] and "3500 s" in item[3]
    g.techs.add("IMPERIAL_AGE")
    item, = [i for i in build.items(g) if i[2] == "Wonder"]
    assert item[1] == "weathered_cut_copper_stairs" and "Needs" not in item[3]
    assert len(build.MENU) <= 54                                       # 6 rows: the most of the plugin menu (#1873)


def test_a_wonder_site_costs_the_aoe2_resources_and_finishes_after_its_build_time():
    data = grid([[64] * 48 for _ in range(48)], [])
    data["objects"].append({"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v0"})
    data.update(tile_size=4, level_height=1, players={"1": {"color": "blue", "arch": "western"}})
    server = Server({"Steve": {"Pos": (9.5, 64.0, 9.5), "Rotation": DOWN}, "v0": {"Pos": (40.5, 64.0, 40.5)}},
                    chosen=build.MENU.index("WONDER") + 1)
    g = gather.Gather(server, data).setup()
    g.techs |= set(build.AGE_TECHS)
    g.stock.update(wood=1200, gold=1100, stone=1000)
    g.click("Steve")
    site, = g.sites
    assert site["name"] == "WONDER" and footprint("WONDER") == 5
    x0, x1, z0, z1 = site["footprint"]
    assert (x1 - x0, z1 - z0) == (5 * 4, 5 * 4)
    assert (g.stock["wood"], g.stock["gold"], g.stock["stone"]) == (200, 100, 0)
    assert not build.rise(g, site, 3499) and build.rise(g, site, 1)
    assert site["done"] and any(c.startswith(("setblock", "fill")) for c in site["commands"])   # the design of buildings.py
