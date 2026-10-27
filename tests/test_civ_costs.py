"""game/civs.py: a player pays the cost of the own civilization for units, technologies and buildings (AoE2 DE, #1091)."""
from urllib.parse import unquote

from test_gather import FakeServer, grid

from game import build, civs, gather, train


def setup(civ, feudal=True, **stock):
    """A flat 24 × 24 map (tile size 1) of player 1 of civilization civ: a town center at blocks x 2-4, z 2-4 and a
    built stable at x 10-12, z 2-4."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]}]
    data = grid([[64] * 24 for _ in range(24)], objects)
    data["players"], data["level_height"] = {"1": {"civ": civ, "color": "blue", "arch": "western"}}, 1
    server = FakeServer({})
    g = gather.Gather(server, data, start={}).setup()
    g.sites.append({"name": "STABLE", "player": 1, "footprint": [10, 13, 2, 5], "done": True})
    g.stock.update(stock)
    if feudal:
        g.techs.add("FEUDAL_AGE")
    return server, g


def test_a_hindustani_villager_costs_less_in_each_age():
    _, g = setup("HINDUSTANIS", food=100)
    assert train.queue(g, "Steve", (3, 3)) and g.stock["food"] == 100 - 44        # 50 food, 13 % cheaper in the Feudal Age
    _, g = setup("GOTHS", food=100)
    assert train.queue(g, "Steve", (3, 3)) and g.stock["food"] == 50


def test_burgundian_bloodlines_costs_half_in_the_menu_and_in_the_payment():
    server, g = setup("BURGUNDIANS", food=75, gold=50)
    rect = train.open_menu(g, "Steve", (11, 3))
    menu = [unquote(c) for c in server.log if c.startswith("aoe menu ")][-1]
    assert ":book:Bloodlines:75 food · 50 gold · " in menu
    assert train.order(g, "Steve", rect, 1) == 1 and g.stock["food"] == 0 and g.stock["gold"] == 0
    assert train.cancel(g, "Steve", rect, 0) == "BLOODLINES" and g.stock == g.stock | {"food": 75, "gold": 50}


def test_a_teutonic_farm_costs_40_percent_less():
    _, g = setup("TEUTONS", wood=36)
    lore = next(lore for _, _, name, lore in build.items(g) if name == "Farm")
    assert lore.startswith("36 wood\n")
    site = build.found(g, "FARM", (14, 16, 14, 16))
    assert site["name"] == "FARM" and g.stock["wood"] == 0
    assert next(lore for _, _, name, lore in build.items() if name == "Farm").startswith("60 wood\n")   # no player


def test_more_cost_bonuses():
    def price(civ, name, *techs):
        _, g = setup(civ, feudal=False)
        g.techs.update(techs)
        return (build.price if name in build.COSTS else train.price)(g, name)
    assert price("BYZANTINES", "SPEARMAN") == {"food": 26, "wood": 19}               # the AoE2 rounding
    assert price("BYZANTINES", "IMPERIAL_AGE", "FEUDAL_AGE", "CASTLE_AGE") == {"food": 667, "gold": 533}
    assert price("CHINESE", "LOOM") == train.COSTS["LOOM"] and price("CHINESE", "LOOM", "FEUDAL_AGE") == {"gold": 48}
    assert price("SPANISH", "FORGING") == {"food": 150} and price("VIKINGS", "WHEELBARROW") == {}
    assert price("CUMANS", "STABLE") == {"wood": 100} and price("MALIANS", "FARM") == build.COSTS["FARM"]
    assert price("BRITONS", "TOWN_CENTER", "FEUDAL_AGE", "CASTLE_AGE")["wood"] == 138             # 275 / 2, half up
    assert price("PORTUGUESE", "MILITIA") == {"food": 50, "gold": 16}


def test_the_table_is_in_order_and_names_known_groups():
    assert list(civs.COSTS) == sorted(civs.COSTS) and set(civs.COSTS) <= set(train.UNIQUE)
    names = set(train.COSTS) | set(build.COSTS)
    for civ, rules in civs.COSTS.items():
        for what, r, change in rules:
            assert len(change) == 4 and r in (None, "food", "wood", "gold", "stone"), civ
            assert isinstance(what, tuple) or what in civs.GROUPS or what in ("ages", "buildings", "buildings but farms",
                                                                               "technologies"), (civ, what)
            assert any(civs.has(what, n) for n in names) or civ in ("BYZANTINES", "DRAVIDIANS", "FRANKS", "HUNS",
                                                                     "ITALIANS", "MALAY", "ROMANS", "SLAVS"), (civ, what)
