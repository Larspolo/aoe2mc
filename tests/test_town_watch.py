"""Town Watch (#1454): the town center researches it in the Feudal Age (AoE2 wiki "Town Watch (Age of
Empires II)"), and then each own building but the walls, gates, farms and fish traps sees 4 tiles more in the fog of
war of the game program."""
from test_fog_seen import T, bare, circle
from test_wheelbarrow import menus, setup

from game import combat, train

# .get: the Antiquity rules have no Town Watch, and their tests import the helpers of this file
FOOD = train.COSTS.get("TOWN_WATCH", {}).get("food", 0)


def test_the_town_center_menu_shows_it_from_the_feudal_age():
    server, g = setup(FOOD, 0)
    g.techs -= {"FEUDAL_AGE"}
    train.open_menu(g, "Steve", (3, 3))
    label = train.ITEMS["TOWN_WATCH"][2]
    assert label not in menus(server)[-1]                              # the Dark Age
    g.techs.add("FEUDAL_AGE")
    train.open_menu(g, "Steve", (3, 3))
    assert f":{label}:" in menus(server)[-1]


def test_the_research_ends_after_its_time():
    server, g = setup(FOOD, 0)
    assert train.order(g, "Steve", train.open_menu(g, "Steve", (3, 3)), train.ITEMS["TOWN_WATCH"][0]) == 1
    assert g.stock["food"] == 0
    train.tick(g, train.TRAIN_TIMES["TOWN_WATCH"] - 1)
    assert "TOWN_WATCH" not in g.techs
    train.tick(g, 1)
    assert "TOWN_WATCH" in g.techs


def tiles(techs):
    tc = {"kind": "building", "name": "TOWN_CENTER", "player": 1, "footprint": [40 * T, 40 * T, 44 * T, 44 * T]}
    wall = {"kind": "building", "name": "STONE_WALL", "player": 1, "footprint": [80 * T, 80 * T, 81 * T, 81 * T]}
    farm = {"kind": "building", "name": "FARM", "player": 1, "footprint": [80 * T, 20 * T, 83 * T, 23 * T]}
    g = bare([tc, wall, farm])
    g.techs = set(techs)
    return g.seen_tiles({"v": (20.5 * T, 70.0, 20.5 * T), "m": (20.5 * T, 70.0, 100.5 * T)})


def test_the_own_buildings_see_4_tiles_more_after_town_watch():
    before, after = tiles(()), tiles({"TOWN_WATCH"})
    r = combat.sight("TOWN_CENTER")
    assert (42, 42 - r) in before and (42, 42 - r - 4) not in before
    assert (42, 42 - r - 4) in after and (42, 42 - r - 5) not in after
    for x0, y0 in ((80, 80), (80, 20), (20, 20), (20, 100)):             # a wall, a farm and two units see as before
        near = lambda s: {(x, y) for x, y in s if abs(x - x0) < 7 and abs(y - y0) < 7}   # noqa: E731
        assert near(after) == near(before)
    assert circle(20, 20, combat.sight("VILLAGER")) <= after
