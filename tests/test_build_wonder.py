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
    g.techs.add("IMPERIAL_AGE")
    open_, = [i for i in build.items(g) if i[2] == "Wonder"]
    assert open_[1] != build.LOCKED and "Needs" not in open_[3] and item[3] == open_[3] + "\nNeeds the Imperial Age"
    assert len(build.MENU) <= 54                                       # 6 rows: the most of the plugin menu (#1873)


def test_a_wonder_site_costs_the_aoe2_resources_and_finishes_after_its_build_time():
    data = grid([[64] * 48 for _ in range(48)], [])
    data["objects"].append({"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v0"})
    data.update(tile_size=4, level_height=1, players={"1": {"color": "blue", "arch": "western"}})
    server = Server({"Steve": {"Pos": (9.5, 64.0, 9.5), "Rotation": DOWN}, "v0": {"Pos": (40.5, 64.0, 40.5)}},
                    chosen=build.MENU.index("WONDER") + 1)
    g = gather.Gather(server, data).setup()
    g.techs |= set(build.AGE_TECHS)
    cost = build.price(g, "WONDER")
    g.stock.update({r: cost.get(r, 0) + extra for r, extra in (("wood", 200), ("gold", 100), ("stone", 0))})
    g.click("Steve")
    site, = g.sites
    n = footprint("WONDER")
    assert site["name"] == "WONDER"
    x0, x1, z0, z1 = site["footprint"]
    assert (x1 - x0, z1 - z0) == (n * 4, n * 4)
    assert (g.stock["wood"], g.stock["gold"], g.stock["stone"]) == (200, 100, 0)
    assert not build.rise(g, site, build.BUILD_TIMES["WONDER"] - 1) and build.rise(g, site, 1)
    assert site["done"] and any(c.startswith(("setblock", "fill")) for c in site["commands"])   # the design of buildings.py
