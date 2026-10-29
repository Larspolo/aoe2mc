"""game/train.py: the Spartans get a free Polemarch at a town center in the Civic (Feudal) and the Classical (Castle) Age
(#2480, the key "age_units" of game/data/civs.jsonl; AoE2 wiki "Polemarch")."""
from test_age_bonuses import advance, game
from test_feudal_age import add

from game import train


def polemarchs(server):
    return sum(c.startswith("summon ") and "Polemarch" in c for c in server.log)


def test_a_spartan_player_gets_a_polemarch_at_each_age():
    for civ in ("SPARTANS", "BRITONS"):
        units = train.civs.value("age_units", civ, {})                 # the free unit of each age, from the data
        new = int(units.get("FEUDAL_AGE") == "POLEMARCH")
        more = new + int(units.get("CASTLE_AGE") == "POLEMARCH")
        server, g = game(civ, food=2000, gold=2000)
        add(g, "BARRACKS", "MILL")
        pop = g.pop
        advance(g)
        assert polemarchs(server) == new and g.pop - pop == new, civ
        assert list(g.soldiers.values()).count("POLEMARCH") == new, civ
        add(g, "MARKET", "BLACKSMITH")
        advance(g, "CASTLE_AGE")
        assert polemarchs(server) == more, civ                          # a census counts the population again
        assert list(g.soldiers.values()).count("POLEMARCH") == more, civ
