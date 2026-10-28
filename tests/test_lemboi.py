"""The Lembos (plural Lemboi) of Chronicles at the dock (#2482): the AoE2 wiki "Lembos" infobox (MediaWiki API,
2026-10-28), only for the Chronicles civilizations. The Puru bonus (wiki "Puru"): Lemboi cost -10/19/27 % and gain
+1/2/3 attack in the Civic/Classical/Imperial Age (the Feudal, Castle and Imperial Age of the game program)."""
import types

from game import civs, combat, fleet, train

AGES = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")
CHRONICLES = {"ACHAEMENIDS", "ATHENIANS", "MACEDONIANS", "PURU", "SPARTANS", "THRACIANS"}


def game(civ, age=0):
    return types.SimpleNamespace(data={"players": {"1": {"civ": civ}}}, player=1, techs=set(AGES[:age]))


def test_the_lembos_is_a_ship_of_the_dock():
    assert (train.COSTS["LEMBOS"], train.TRAIN_TIMES["LEMBOS"]) == ({"food": 30, "wood": 50}, 60)
    assert combat.SHIP in combat.stats("LEMBOS").classes and "LEMBOS" in fleet.SPEEDS and "LEMBOS" in combat.MELEE_RANGED
    assert "LEMBOS" in train.TRAINS["DOCK"]


def test_only_the_chronicles_civilizations_train_the_lembos():
    every = set().union(*train.civs.MISSING.values())
    assert every - set(train.civs.MISSING["LEMBOS"]) == CHRONICLES
    assert "BRITONS" in train.civs.MISSING["LEMBOS"]


def test_the_puru_lemboi_cost_less_and_attack_more_in_each_age():
    base, s = train.COSTS["LEMBOS"], combat.stats("LEMBOS")
    for age, cost, attack in ((0, {"food": 30, "wood": 50}, 0), (1, {"food": 27, "wood": 45}, 1),
                              (2, {"food": 24, "wood": 41}, 2), (3, {"food": 22, "wood": 37}, 3)):
        assert civs.cost(game("PURU", age), "LEMBOS", base) == cost, age
        assert civs.units(game("PURU", age), "LEMBOS", s).attack == s.attack + attack, age
    assert civs.cost(game("ATHENIANS", 3), "LEMBOS", base) == base     # no bonus for the others
    assert civs.units(game("ATHENIANS", 3), "LEMBOS", s) == s
    assert civs.units(game("PURU", 3), "GALLEY", combat.stats("GALLEY")) == combat.stats("GALLEY")
