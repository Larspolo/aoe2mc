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


def test_a_hindustani_villager_costs_less_than_a_goth_one():
    _, g = setup("HINDUSTANIS", food=100)
    pay = train.price(g, "VILLAGER_MALE")["food"]
    assert pay < train.COSTS["VILLAGER_MALE"]["food"]
    assert train.queue(g, "Steve", (3, 3)) and g.stock["food"] == 100 - pay
    _, g = setup("GOTHS", food=100)
    assert train.queue(g, "Steve", (3, 3)) and g.stock["food"] == 100 - train.COSTS["VILLAGER_MALE"]["food"]


def test_burgundian_bloodlines_costs_less_in_the_menu_and_in_the_payment():
    server, g = setup("BURGUNDIANS", food=1000, gold=1000)
    pay = train.price(g, "BLOODLINES")
    assert sum(pay.values()) < sum(train.COSTS["BLOODLINES"].values())
    rect = train.open_menu(g, "Steve", (11, 3))
    menu = [unquote(c) for c in server.log if c.startswith("aoe menu ")][-1]
    assert ":book:Bloodlines:" + " · ".join(f"{v} {r}" for r, v in pay.items()) + " · " in menu
    assert train.order(g, "Steve", rect, train.layout(g, rect)["BLOODLINES"][0]) == 1
    assert (g.stock["food"], g.stock["gold"]) == (1000 - pay.get("food", 0), 1000 - pay.get("gold", 0))
    assert train.cancel(g, "Steve", rect, 0) == "BLOODLINES" and (g.stock["food"], g.stock["gold"]) == (1000, 1000)


def test_a_teutonic_farm_costs_less():
    _, g = setup("TEUTONS", wood=1000)
    wood = build.price(g, "FARM")["wood"]
    assert wood < build.COSTS["FARM"]["wood"]
    lore = next(lore for _, _, name, lore in build.items(g) if name == "Farm")
    assert lore.startswith(f"{wood} wood\n")
    site = build.found(g, "FARM", (14, 16, 14, 16))
    assert site["name"] == "FARM" and g.stock["wood"] == 1000 - wood
    assert next(lore for _, _, name, lore in build.items() if name == "Farm").startswith(
        f"{build.COSTS['FARM']['wood']} wood\n")                     # no player


def test_the_table_is_in_order_and_names_known_groups():
    assert list(civs.COSTS) == sorted(civs.COSTS) and set(civs.COSTS) <= {r["name"] for r in civs.ROWS}
    names = set(train.COSTS) | set(build.COSTS)
    for civ, rules in civs.COSTS.items():
        for what, r, change in rules:
            assert len(change) == 4 and r in (None, "food", "wood", "gold", "stone"), civ
            assert isinstance(what, tuple) or what in civs.GROUPS or what in ("ages", "buildings", "buildings but farms",
                                                                               "technologies") \
                or what.split()[0] in train.TRAINS and what.endswith(" technologies"), (civ, what)
            assert any(civs.has(what, n) for n in names) or civ in ("BYZANTINES", "DRAVIDIANS", "FRANKS", "HUNS",
                                                                     "ITALIANS", "MALAY", "ROMANS", "SLAVS"), (civ, what)
