"""The Houfnice and the Heavy Rocket Cart have their AoE2 DE values and shoot as siege units (#1085)."""
from game import combat


def test_the_values_of_the_wiki():
    h, r = combat.stats("HOUFNICE"), combat.stats("HEAVY_ROCKET_CART")
    assert (h.hp, h.attack, h.melee, h.pierce, h.range, h.reload) == (90, 50, 2, 6, 12, 6.5)
    assert h.bonus == {"building": 250, combat.HSI: 50, combat.SIE: 20} and combat.SIE in h.classes   # +50 heavy siege (#2143)
    assert (r.hp, r.attack, r.melee, r.pierce, r.range, r.reload) == (65, 5, 0, 8, 8, 5.35)
    assert r.bonus == {"building": 12, combat.SIE: 2} and "HEAVY_ROCKET_CART" in combat.MELEE_RANGED


def test_both_get_a_siege_range_with_their_blast():
    assert combat.range_command("u", "HOUFNICE", 4).split()[3:6] == ["48", str(round(6.5 / 1.7 * 20)), "2.8"]
    assert combat.range_command("u", "HEAVY_ROCKET_CART", 4).split()[5] == "5.0"     # then the minimum range (#1350)
    assert combat.range_command("u", "ROCKET_CART", 4).split()[5] == "4.0"
