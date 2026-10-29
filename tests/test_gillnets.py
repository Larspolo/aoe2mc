"""game/train.py and game/fleet.py: the dock researches Fishing Lines in the Feudal Age and Gillnets after it in the
Castle Age, in one slot: each one makes the own fishing ships gather faster and carry more food (#1439, AoE2 DE wiki
infoboxes). Fake server, no Minecraft."""
from urllib.parse import unquote

from menu_line import item
from test_ship_gather import fish_map, play

from game import fleet, gather, train

DOCK = (15, 12)


def menus(server):
    return [unquote(c) for c in server.log if c.startswith("aoe menu ")]


def test_the_dock_menu_shows_fishing_lines_in_the_feudal_age_and_then_gillnets_in_the_castle_age():
    server, g, uuid = fish_map()
    train.open_menu(g, "Steve", DOCK)
    assert "Fishing Lines" not in menus(server)[-1]                    # the Dark Age
    g.techs.add("FEUDAL_AGE")
    train.open_menu(g, "Steve", DOCK)
    assert item(menus(server)[-1], "Fishing Lines").endswith(" · research")
    g.techs.add("CASTLE_AGE")
    train.open_menu(g, "Steve", DOCK)
    assert "Gillnets" not in menus(server)[-1] and train.queue(g, "Steve", DOCK, "GILLNETS") is None
    g.techs.add("FISHING_LINES")
    train.open_menu(g, "Steve", DOCK)
    assert item(menus(server)[-1], "Gillnets").endswith(" · research")


def test_each_research_makes_the_ships_gather_faster_and_carry_more():
    server, g, uuid = fish_map()
    g.techs |= {"FEUDAL_AGE", "CASTLE_AGE"}
    g.stock.update(food=5000, wood=5000)
    assert fleet.rate(g, (20, 12)) == gather.SHIP_WORK["deep"]
    old = fleet.rate(g, (20, 12)), fleet.rate(g, (14, 3)), fleet.carry(g)
    for tech in ("FISHING_LINES", "GILLNETS"):
        rect = train.open_menu(g, "Steve", DOCK)
        assert train.order(g, "Steve", rect, train.ITEMS[tech][0]) == 1
        train.tick(g, train.TRAIN_TIMES[tech])
        assert tech in g.techs
        new = fleet.rate(g, (20, 12)), fleet.rate(g, (14, 3)), fleet.carry(g)   # deep fish, shore fish, load
        assert all(b > a for a, b in zip(old, new)), tech
        old = new
    v = g.ships[uuid]
    start = g.map.fish[20, 12]
    fleet.fish(g, {uuid}, (20, 12))
    play(g, 10)
    assert v.state == "chop"
    load = v.load
    play(g, 20)                                                         # the food of 20 game seconds
    assert abs(v.load - load - 20 * fleet.rate(g, (20, 12))) <= 1.5
    play(g, 30)
    carry = fleet.carry(g)
    assert v.load <= carry and g.map.fish[20, 12] == start - carry - v.load * (v.state == "chop")
