"""game/train.py and game/fleet.py: the dock researches Fishing Lines in the Feudal Age (50 food, 100 wood, 20 s) and
Gillnets after it in the Castle Age (150 food, 200 wood, 45 s), in one slot: each one makes the own fishing ships
gather 10 % faster and carry 5 more food (#1439, AoE2 DE wiki infoboxes). Fake server, no Minecraft."""
from urllib.parse import unquote

import pytest
from test_ship_gather import fish_map, play

from game import fleet, gather, train

DOCK = (15, 12)


def menus(server):
    return [unquote(c) for c in server.log if c.startswith("aoe menu ")]


def test_the_cost_time_age_and_slot_are_those_of_aoe2():
    assert (train.COSTS["FISHING_LINES"], train.TRAIN_TIMES["FISHING_LINES"], train.TECH_AGE["FISHING_LINES"]) == \
        ({"food": 50, "wood": 100}, 20, 1)
    assert (train.COSTS["GILLNETS"], train.TRAIN_TIMES["GILLNETS"], train.TECH_AGE["GILLNETS"]) == \
        ({"food": 150, "wood": 200}, 45, 2)
    assert train.AFTER["GILLNETS"] == "FISHING_LINES" and train.ITEMS["GILLNETS"][0] == train.ITEMS["FISHING_LINES"][0]
    assert {"FISHING_LINES", "GILLNETS"} <= set(train.TRAINS["DOCK"])


def test_the_dock_menu_shows_fishing_lines_in_the_feudal_age_and_then_gillnets_in_the_castle_age():
    server, g, uuid = fish_map()
    slot = train.ITEMS["FISHING_LINES"][0]
    train.open_menu(g, "Steve", DOCK)
    assert "Fishing Lines" not in menus(server)[-1]                    # the Dark Age
    g.techs.add("FEUDAL_AGE")
    train.open_menu(g, "Steve", DOCK)
    assert f" {slot}:book:Fishing Lines:50 food · 100 wood · 20 s · research " in menus(server)[-1] + " "
    g.techs.add("CASTLE_AGE")
    train.open_menu(g, "Steve", DOCK)
    assert "Gillnets" not in menus(server)[-1] and train.queue(g, "Steve", DOCK, "GILLNETS") is None
    g.techs.add("FISHING_LINES")
    train.open_menu(g, "Steve", DOCK)
    assert f" {slot}:book:Gillnets:150 food · 200 wood · 45 s · research " in menus(server)[-1] + " "


def test_each_research_makes_the_ships_gather_10_percent_faster_and_carry_5_more():
    server, g, uuid = fish_map()
    g.techs |= {"FEUDAL_AGE", "CASTLE_AGE"}
    g.stock.update(food=500, wood=500)
    assert (fleet.rate(g, (20, 12)), fleet.carry(g)) == (gather.SHIP_WORK["deep"], 15)
    for tech, n in (("FISHING_LINES", 1), ("GILLNETS", 2)):
        rect = train.open_menu(g, "Steve", DOCK)
        assert train.order(g, "Steve", rect, train.ITEMS[tech][0]) == 1
        train.tick(g, train.TRAIN_TIMES[tech])
        assert tech in g.techs
        assert fleet.rate(g, (20, 12)) == pytest.approx(0.42 * 1.1 ** n)
        assert fleet.rate(g, (14, 3)) == pytest.approx(0.24 * 1.1 ** n)   # the shore fish
        assert fleet.carry(g) == 15 + 5 * n
    v = g.ships[uuid]
    fleet.fish(g, {uuid}, (20, 12))
    play(g, 10)
    assert v.state == "chop"
    load = v.load
    play(g, 20)                                                         # 0.42 × 1.21 = 0.51 food per game second
    assert v.load - load in (9, 10, 11)
    play(g, 30)
    assert v.load <= 25 and g.map.fish[20, 12] == 225 - 25 - v.load * (v.state == "chop")
