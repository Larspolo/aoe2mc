"""game/train.py: the university researches Masonry in the Castle Age (AoE2 DE wiki "Masonry"), #1398. The complete
and the new own buildings get more hit points and armor; a damaged building keeps its lost hit points; the walls and
gates do not change."""
import math

from menu_line import item
from test_loom import menus
from test_tower_upgrades import MAP, NEW, research, setup, uuid

from game import build, combat, repair, train

TC = (2, 5, 2, 5)


def test_the_university_menu_shows_masonry_in_the_castle_age():
    for age, shown in ((1, False), (2, True)):
        server, g = setup(age)
        train.open_menu(g, "Steve", (9, 9))
        assert (":book:Masonry:" in menus(server)[-1]) == shown
    assert item(menus(server)[-1], "Masonry").endswith(" · research")


def masonry(name, *techs):
    """The values of the own building name with the technologies, without and with Masonry."""
    _, g = setup()
    g.techs |= set(techs)
    old = build.values(g, name)
    g.techs.add("MASONRY")
    return old, build.values(g, name)


def test_the_values_of_masonry():
    for name, techs in (("HOUSE", ()), ("WATCH_TOWER", ()), ("WATCH_TOWER", ("GUARD_TOWER",))):   # also a guard tower
        old, new = masonry(name, *techs)
        assert new.hp > old.hp and new.melee > old.melee and new.pierce > old.pierce, name
        assert new._replace(hp=old.hp, melee=old.melee, pierce=old.pierce) == old, name   # the attack stays
    assert masonry("STONE_WALL")[1] == combat.stats("STONE_WALL")          # no change for walls and gates


def test_the_research_gives_the_own_buildings_more_hit_points_and_armor():
    server, g = setup()
    (old, tower), (_, tc) = masonry("WATCH_TOWER"), masonry("TOWN_CENTER")
    server.hp[uuid(MAP)], server.hp[uuid(TC)] = old.hp - 500, combat.stats("TOWN_CENTER").hp   # the tower lost 500
    research(g, "MASONRY")
    assert server.hp[uuid(MAP)] == tower.hp - 500 and server.hp[uuid(TC)] == tc.hp
    assert any(c.startswith(f"aoe building {uuid(MAP)} {tower.hp} {tower.melee} {tower.pierce} ") for c in server.log)
    assert any(c.startswith(f"aoe building {uuid(TC)} {tc.hp} {tc.melee} {tc.pierce} ") for c in server.log)
    assert not any(c.startswith("summon ") for c in server.log)    # the same targets


def test_a_new_building_after_the_research_has_the_values_of_masonry():
    server, g = setup()
    g.techs.add("MASONRY")
    site = build.found(g, "WATCH_TOWER", NEW)
    server.log.clear()
    build.rise(g, site, math.inf)
    tower = masonry("WATCH_TOWER")[1]
    assert any(c.startswith(f"aoe building {uuid(NEW)} {tower.hp} {tower.melee} {tower.pierce} ") for c in server.log)


def test_villagers_repair_to_the_hit_points_of_masonry():
    _, g = setup()
    old, new = masonry("TOWN_CENTER")
    assert repair.full(g, "TOWN_CENTER", 1) == old.hp
    g.techs.add("MASONRY")
    assert repair.full(g, "TOWN_CENTER", 1) == new.hp > old.hp
