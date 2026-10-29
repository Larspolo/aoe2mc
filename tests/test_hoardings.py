"""Hoardings (#1456): the castle researches it in the Imperial Age (AoE2 wiki "Hoardings"), and then the complete and
the new own castles have more hit points; a damaged castle keeps its lost hit points."""
import math

from menu_line import item
from test_gather import grid
from test_loom import menus
from test_repair import HpServer

from game import build, combat, gather, repair, train

CASTLE, NEW = (10, 14, 2, 6), (16, 20, 10, 14)                     # block footprints (x0, x1, z0, z1), tile size 1


def setup(age=3):
    """A flat 24 × 24 map with an own town center and castle, the first `age` ages and the stock for the research."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "building", "name": "CASTLE", "player": 1, "tile": [12.0, 4.0], "footprint": [10, 2, 14, 6]}]
    data = grid([[64] * 24 for _ in range(24)], objects)
    data["players"], data["level_height"] = {"1": {"civ": "BRITONS", "color": "blue", "arch": "western"}}, 1
    server = HpServer({}, {})
    g = gather.Gather(server, data).setup()
    g.techs |= set(build.AGE_TECHS[:age])
    g.stock.update(food=4000, wood=4000)
    return server, g


def uuid(rect):
    x0, x1, z0, z1 = rect
    return combat.target_uuid([x0, z0, x1, z1])


def hoardings_hp():
    """The hit points of a castle after Hoardings."""
    _, g = setup()
    g.techs.add("HOARDINGS")
    return build.values(g, "CASTLE").hp


def test_only_the_castles_get_more_hit_points():
    _, g = setup()
    g.techs.add("HOARDINGS")
    assert build.values(g, "CASTLE").hp > combat.stats("CASTLE").hp
    assert build.values(g, "TOWN_CENTER") == combat.stats("TOWN_CENTER")


def test_the_castle_menu_shows_it_in_the_imperial_age():
    for age, shown in ((2, False), (3, True)):
        server, g = setup(age)
        train.open_menu(g, "Steve", (12, 4))
        assert (":book:Hoardings:" in menus(server)[-1]) == shown
    assert item(menus(server)[-1], "Hoardings").endswith(" · research")


def test_the_research_gives_the_own_castles_more_hit_points():
    server, g = setup()
    hp = hoardings_hp()
    server.hp[uuid(CASTLE)] = combat.stats("CASTLE").hp - 500         # the castle lost 500 hit points
    assert train.order(g, "Steve", train.open_menu(g, "Steve", (12, 4)), train.ITEMS["HOARDINGS"][0]) == 1
    train.tick(g, train.seconds(g, "HOARDINGS", "CASTLE") - 1)
    assert "HOARDINGS" not in g.techs
    train.tick(g, 1)
    assert "HOARDINGS" in g.techs and server.hp[uuid(CASTLE)] == hp - 500
    assert any(c.startswith(f"aoe building {uuid(CASTLE)} {hp} ") for c in server.log)
    assert repair.full(g, "CASTLE", 1) == hp


def test_a_new_castle_after_the_research_has_the_hit_points_of_hoardings():
    server, g = setup()
    g.techs.add("HOARDINGS")
    site = build.found(g, "CASTLE", NEW)
    server.log.clear()
    build.rise(g, site, math.inf)
    assert any(c.startswith(f"aoe building {uuid(NEW)} {hoardings_hp()} ") for c in server.log)
