"""Town Patrol (#1579): the town center researches it in the Castle Age after Town Watch (300 food, 100 gold, 40 s;
AoE2 wiki "Town Patrol"), and then each own building but the walls, gates, farms and fish traps sees 4 tiles more
again in the fog of war of the game program."""
from test_town_watch import tiles
from test_wheelbarrow import menus, setup

from game import combat, train


def test_the_values_are_those_of_aoe2():
    assert train.COSTS["TOWN_PATROL"] == {"food": 300, "gold": 100} and train.TRAIN_TIMES["TOWN_PATROL"] == 40
    assert train.TECH_AGE["TOWN_PATROL"] == 2 and train.AFTER["TOWN_PATROL"] == "TOWN_WATCH"
    assert len(train.HELP["TOWN_PATROL"]) <= 50 and train.ITEMS["TOWN_PATROL"][0] == train.ITEMS["TOWN_WATCH"][0]
    t = train.TRAINS["TOWN_CENTER"]
    assert t.index("TOWN_WATCH") < t.index("TOWN_PATROL")


def test_the_town_center_menu_shows_it_in_the_castle_age_after_town_watch():
    server, g = setup(300, 100)
    g.techs |= {"FEUDAL_AGE", "CASTLE_AGE"}
    train.open_menu(g, "Steve", (3, 3))
    assert "Town Patrol" not in menus(server)[-1] and "Town Watch" in menus(server)[-1]
    g.techs -= {"CASTLE_AGE"}
    g.techs.add("TOWN_WATCH")
    train.open_menu(g, "Steve", (3, 3))
    assert "Town Patrol" not in menus(server)[-1]                      # the Feudal Age
    g.techs.add("CASTLE_AGE")
    train.open_menu(g, "Steve", (3, 3))
    assert " 6:book:Town Patrol:300 food · 100 gold · 40 s · research" in menus(server)[-1]


def test_the_research_ends_after_40_seconds():
    server, g = setup(300, 100)
    g.techs |= {"FEUDAL_AGE", "CASTLE_AGE", "TOWN_WATCH"}
    assert train.order(g, "Steve", train.open_menu(g, "Steve", (3, 3)), train.ITEMS["TOWN_PATROL"][0]) == 1
    assert g.stock["food"] == 0 and g.stock["gold"] == 0
    train.tick(g, 39)
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
