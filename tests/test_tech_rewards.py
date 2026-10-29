"""game/train.py: the rewards of a research (#2175, game/civs.py TECH_GIFTS and the key "economy_villagers"): the Spanish get
gold for each technology but an age, and the Wei get one free villager at a town center for each economic technology
(AoE2 DE wiki, "Spanish" and "Wei")."""
from test_age_bonuses import advance, game
from test_feudal_age import add

from game import civs, train


def research(g, name):
    train.research(g, {"name": name, "player": "Steve"})


def test_a_spanish_player_gets_gold_for_a_technology():
    for civ, spanish in (("SPANISH", True), ("BRITONS", False)):
        server, g = game(civ, gold=0)
        research(g, "LOOM")
        gold = g.stock["gold"]
        assert (gold > 0) == spanish, civ
        assert (f"scoreboard players add Gold aoe_res {gold}" in server.log) == spanish, civ


def test_a_spanish_player_gets_no_gold_for_an_age():
    server, g = game("SPANISH", food=500, gold=0)
    add(g, "BARRACKS", "MILL")
    advance(g)
    assert g.stock["gold"] == 0


def test_a_wei_player_gets_a_villager_for_an_economic_technology():
    wei = civs.value("economy_villagers", "WEI", 0)
    assert wei > 0
    for civ, name in (("WEI", "WHEELBARROW"), ("WEI", "DOUBLE_BIT_AXE"), ("WEI", "LOOM"), ("WEI", "FORGING"),
                      ("BRITONS", "WHEELBARROW")):
        new = wei * (civ == "WEI" and name in civs.ECONOMY)
        server, g = game(civ)
        villagers, pop = len(g.villagers), g.pop
        research(g, name)
        assert len(g.villagers) - villagers == new and g.pop - pop == new, (civ, name)
        assert sum(c.startswith("summon minecraft:villager") for c in server.log) == new, (civ, name)
