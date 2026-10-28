"""game/train.py: the rewards of a research (#2175, game/civs.py TECH_GIFTS and ECONOMY_VILLAGERS): the Spanish get
20 gold for each technology but an age, and the Wei get one free villager at a town center for each economic technology
(AoE2 DE wiki, "Spanish" and "Wei")."""
from test_age_bonuses import advance, game
from test_feudal_age import add

from game import train


def research(g, name):
    train.research(g, {"name": name, "player": "Steve"})


def test_a_spanish_player_gets_20_gold_for_a_technology():
    for civ, gold in (("SPANISH", 20), ("BRITONS", 0)):
        server, g = game(civ, gold=0)
        research(g, "LOOM")
        assert g.stock["gold"] == gold, civ
        assert ("scoreboard players add Gold aoe_res 20" in server.log) == bool(gold), civ


def test_a_spanish_player_gets_no_gold_for_an_age():
    server, g = game("SPANISH", food=500, gold=0)
    add(g, "BARRACKS", "MILL")
    advance(g)
    assert g.stock["gold"] == 0


def test_a_wei_player_gets_a_villager_for_an_economic_technology():
    for civ, name, new in (("WEI", "WHEELBARROW", 1), ("WEI", "DOUBLE_BIT_AXE", 1), ("WEI", "LOOM", 0),
                           ("WEI", "FORGING", 0), ("BRITONS", "WHEELBARROW", 0)):
        server, g = game(civ)
        villagers, pop = len(g.villagers), g.pop
        research(g, name)
        assert len(g.villagers) - villagers == new and g.pop - pop == new, (civ, name)
        assert sum(c.startswith("summon minecraft:villager") for c in server.log) == new, (civ, name)
