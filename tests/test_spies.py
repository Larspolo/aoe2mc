"""Spies (#2193): the castle researches it in the Imperial Age (1 s; AoE2 DE wiki "Spies": 200 gold per enemy civilian
unit, at least 200 and at most 30,000 gold), and then the player sees all enemy units: the fog of war shows the hidden
enemy units at once and hides no unit after it (fog.reveal, fog.tick)."""
from test_hoardings import setup
from test_loom import menus

from game import fog, train

E1, E2 = "00000000-0000-0000-0000-00000000e001", "00000000-0000-0000-0000-00000000e002"


def spies(age=3, enemies=None):
    server, g = setup(age)
    g.enemies = {E1: "VILLAGER_MALE", E2: "MILITIA"} if enemies is None else enemies
    g.stock.update(gold=400)
    return server, g


def test_the_values_are_those_of_aoe2():
    assert "SPIES" in train.TRAINS["CASTLE"] and len(train.HELP["SPIES"]) <= 50


def test_the_cost_is_200_gold_for_each_enemy_civilian_from_200_to_30000():
    _, g = spies()
    assert train.price(g, "SPIES") == {"gold": 200}                    # one villager; the militia is not civilian
    g.enemies = {f"e{i}": n for i, n in enumerate(["VILLAGER_FEMALE", "TRADE_CART_EMPTY", "FISHING_SHIP", "KNIGHT"])}
    assert train.price(g, "SPIES") == {"gold": 600}
    g.enemies = {}
    assert train.price(g, "SPIES") == {"gold": 200}                    # the minimum
    g.enemies = {f"e{i}": "VILLAGER_MALE" for i in range(200)}
    assert train.price(g, "SPIES") == {"gold": 30000}                  # the maximum


def test_the_castle_menu_shows_it_in_the_imperial_age():
    for age, shown in ((2, False), (3, True)):
        server, g = spies(age)
        train.open_menu(g, "Steve", (12, 4))
        assert (":book:Spies:" in menus(server)[-1]) == shown
    assert "18:book:Spies:200 gold · 1 s" in menus(server)[-1]


def test_the_research_shows_the_hidden_enemy_units_and_the_fog_hides_no_more():
    server, g = spies()
    g.paper = True
    vars(g)["fog"] = {"hidden": {E1, E2}, "at": None}
    assert train.order(g, "Steve", train.open_menu(g, "Steve", (12, 4)), train.ITEMS["SPIES"][0]) == 1
    assert g.stock["gold"] == 200
    assert not any(c.startswith("aoe show") for c in server.log)       # not before the research
    train.tick(g, 1)
    assert "SPIES" in g.techs and f"aoe show @a[team=p1] {E1} {E2}" in server.log
    assert vars(g)["fog"]["hidden"] == set()
    n = len(server.log)
    fog.tick(g)                                                        # no fog: no query of the positions, no hide
    assert server.log[n:] == []
