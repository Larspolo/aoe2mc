"""game/train.py: the university researches Masonry in the Castle Age (150 food, 175 wood, 50 s; AoE2 DE wiki
"Masonry"), #1398. The complete and the new own buildings get +10 % hit points and +1/+1 armor; a damaged building keeps
its lost hit points; the walls and gates do not change."""
import math

from test_loom import menus
from test_tower_upgrades import MAP, NEW, research, setup, uuid

from game import build, combat, repair, train

TC = (2, 5, 2, 5)


def test_the_cost_time_and_age_are_those_of_aoe2():
    assert train.COSTS["MASONRY"] == {"food": 150, "wood": 175} and train.TRAIN_TIMES["MASONRY"] == 50
    assert train.TECH_AGE["MASONRY"] == 2 and "MASONRY" in train.TRAINS["UNIVERSITY"]


def test_the_university_menu_shows_masonry_in_the_castle_age():
    for age, shown in ((1, False), (2, True)):
        server, g = setup(age)
        train.open_menu(g, "Steve", (9, 9))
        assert (":book:Masonry:" in menus(server)[-1]) == shown
    assert "6:book:Masonry:150 food · 175 wood · 50 s · research" in menus(server)[-1]


def test_the_values_of_masonry():
    _, g = setup()
    g.techs.add("MASONRY")
    assert build.values(g, "HOUSE") == combat.Stats(605, 0, 1, 8, 0, 0.0, {}, ("building", combat.STANDARD))
    assert build.values(g, "WATCH_TOWER")[:4] == (1122, 5, 2, 8)
    assert build.values(g, "STONE_WALL") == combat.stats("STONE_WALL")       # no change for walls and gates
    g.techs.add("GUARD_TOWER")
    assert build.values(g, "WATCH_TOWER")[:4] == (1650, 7, 3, 9)            # the guard tower with Masonry


def test_the_research_gives_the_own_buildings_more_hit_points_and_armor():
    server, g = setup()
    server.hp[uuid(MAP)], server.hp[uuid(TC)] = 520, 2400           # the tower lost 500 hit points
    research(g, "MASONRY", 50)
    assert server.hp[uuid(MAP)] == 1122 - 500 and server.hp[uuid(TC)] == 2640
    assert any(c.startswith(f"aoe building {uuid(MAP)} 1122 2 8 ") for c in server.log)
    assert any(c.startswith(f"aoe building {uuid(TC)} 2640 4 6 ") for c in server.log)
    assert not any(c.startswith("summon ") for c in server.log)    # the same targets


def test_a_new_building_after_the_research_has_the_values_of_masonry():
    server, g = setup()
    g.techs.add("MASONRY")
    site = build.found(g, "WATCH_TOWER", NEW)
    server.log.clear()
    build.rise(g, site, math.inf)
    assert any(c.startswith(f"aoe building {uuid(NEW)} 1122 2 8 ") for c in server.log)


def test_villagers_repair_to_the_hit_points_of_masonry():
    _, g = setup()
    assert repair.full(g, "TOWN_CENTER", 1) == 2400
    g.techs.add("MASONRY")
    assert repair.full(g, "TOWN_CENTER", 1) == 2640
