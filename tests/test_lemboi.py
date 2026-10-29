"""The Lembos (plural Lemboi) of Chronicles at the dock (#2482): the AoE2 wiki "Lembos" infobox (MediaWiki API,
2026-10-28), only for the Chronicles civilizations. The Puru bonus (wiki "Puru"): Lemboi cost less and gain attack in
each age from the Civic Age (the Feudal, Castle and Imperial Age of the game program)."""
import types

from game import civs, combat, train

AGES = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def game(civ, age=0):
    return types.SimpleNamespace(data={"players": {"1": {"civ": civ}}}, player=1, techs=set(AGES[:age]))


def test_the_puru_lemboi_cost_less_and_attack_more_in_each_age():
    base, s = train.COSTS["LEMBOS"], combat.stats("LEMBOS")
    assert civs.cost(game("PURU", 0), "LEMBOS", base) == base and civs.units(game("PURU", 0), "LEMBOS", s) == s
    for age in (1, 2, 3):                                              # each age: cheaper and stronger than before
        old, new = (civs.cost(game("PURU", a), "LEMBOS", base) for a in (age - 1, age))
        assert all(new[r] < old[r] for r in base), age
        assert civs.units(game("PURU", age), "LEMBOS", s).attack > civs.units(game("PURU", age - 1), "LEMBOS", s).attack, age
    assert civs.cost(game("ATHENIANS", 3), "LEMBOS", base) == base     # no bonus for the others
    assert civs.units(game("ATHENIANS", 3), "LEMBOS", s) == s
    assert civs.units(game("PURU", 3), "GALLEY", combat.stats("GALLEY")) == combat.stats("GALLEY")
