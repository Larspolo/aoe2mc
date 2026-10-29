"""game/train.py: the university researches Murder Holes in the Castle Age (AoE2 DE wiki, all civilizations), #1547. After it, the defensive buildings of the player (combat.FORT_MIN_RANGE) have no minimum
range: the complete ones get a new `aoe building` command, and the new ones get it from build.minimum."""
import math

from menu_line import item
from test_loom import menus
from test_tower_upgrades import MAP, NEW, research, setup, uuid

from game import build, combat, train


def test_the_university_menu_shows_it_in_the_castle_age():
    for age, shown in ((1, False), (2, True)):
        server, g = setup(age)
        train.open_menu(g, "Steve", (9, 9))
        assert (":book:Murder Holes:" in menus(server)[-1]) == shown
    assert item(menus(server)[-1], "Murder Holes").endswith(" · research")


def test_the_defensive_buildings_lose_their_minimum_range():
    _, g = setup(2)
    assert {n: build.minimum(g, n) for n in combat.FORT_MIN_RANGE} == combat.FORT_MIN_RANGE
    g.techs.add("MURDER_HOLES")
    assert {build.minimum(g, n) for n in combat.FORT_MIN_RANGE} == {0} and build.minimum(g, "TOWN_CENTER") == 0
    box = (0, 64, 0, 1, 70, 1)
    assert combat.building(uuid(MAP), "WATCH_TOWER", 1, box, 4)[-1].split()[15] == "4"     # 1 tile × 4 blocks
    cmd = combat.building(uuid(MAP), "WATCH_TOWER", 1, box, 4, low=build.minimum(g, "WATCH_TOWER"))[-1]
    assert cmd.split()[15] == "0"


def test_the_research_changes_the_own_towers():
    server, g = setup(2)
    server.hp[uuid(MAP)] = 1020                                        # the watch tower of the map
    research(g, "MURDER_HOLES")
    cmds = [c for c in server.log if c.startswith(f"aoe building {uuid(MAP)} ")]
    assert cmds and cmds[-1].split()[15] == "0"


def test_a_new_tower_after_the_research_has_no_minimum_range():
    server, g = setup(2)
    g.techs.add("MURDER_HOLES")
    site = build.found(g, "WATCH_TOWER", NEW)
    server.log.clear()
    build.rise(g, site, math.inf)
    cmds = [c for c in server.log if c.startswith(f"aoe building {uuid(NEW)} ")]
    assert cmds and cmds[-1].split()[15] == "0"
