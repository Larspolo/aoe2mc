"""Town Patrol (#1579): the town center researches it in the Castle Age after Town Watch (AoE2 wiki "Town Patrol"),
and then each own building but the walls, gates, farms and fish traps sees 4 tiles more again in the fog of war of the
game program."""
from test_town_watch import tiles
from test_wheelbarrow import menus, setup

from game import combat, train

COST = train.COSTS["TOWN_PATROL"]


def test_the_town_center_menu_shows_it_in_the_castle_age_after_town_watch():
    server, g = setup(COST.get("food", 0), 0)
    g.stock.update(gold=COST.get("gold", 0))
    g.techs |= {"FEUDAL_AGE", "CASTLE_AGE"}
    train.open_menu(g, "Steve", (3, 3))
    patrol, watch = train.ITEMS["TOWN_PATROL"][2], train.ITEMS["TOWN_WATCH"][2]
    assert patrol not in menus(server)[-1] and watch in menus(server)[-1]
    g.techs -= {"CASTLE_AGE"}
    g.techs.add("TOWN_WATCH")
    train.open_menu(g, "Steve", (3, 3))
    assert patrol not in menus(server)[-1]                             # the Feudal Age
    g.techs.add("CASTLE_AGE")
    train.open_menu(g, "Steve", (3, 3))
    assert f":{patrol}:" in menus(server)[-1] and "research" in menus(server)[-1]


def test_the_research_ends_after_its_time():
    server, g = setup(COST.get("food", 0), 0)
    g.stock.update(gold=COST.get("gold", 0))
    g.techs |= {"FEUDAL_AGE", "CASTLE_AGE", "TOWN_WATCH"}
    assert train.order(g, "Steve", train.open_menu(g, "Steve", (3, 3)), train.ITEMS["TOWN_PATROL"][0]) == 1
    assert g.stock["food"] == 0 and g.stock["gold"] == 0
    train.tick(g, train.TRAIN_TIMES["TOWN_PATROL"] - 1)
    assert "TOWN_PATROL" not in g.techs
    train.tick(g, 1)
    assert "TOWN_PATROL" in g.techs


def test_the_own_buildings_see_4_tiles_more_after_town_patrol():
    watch, patrol = tiles({"TOWN_WATCH"}), tiles({"TOWN_WATCH", "TOWN_PATROL"})
    r = combat.sight("TOWN_CENTER") + 4
    assert (42, 42 - r - 4) not in watch
    assert (42, 42 - r - 4) in patrol and (42, 42 - r - 5) not in patrol
    for x0, y0 in ((80, 80), (80, 20), (20, 20), (20, 100)):             # a wall, a farm and two units see as before
        near = lambda s: {(x, y) for x, y in s if abs(x - x0) < 7 and abs(y - y0) < 7}   # noqa: E731
        assert near(patrol) == near(watch)
