"""The Houfnice and the Heavy Rocket Cart shoot as siege units (#1085)."""
from game import combat


def test_both_get_a_siege_range_with_their_blast():
    h = combat.stats("HOUFNICE")
    assert combat.range_command("u", "HOUFNICE", 4).split()[3:6] == [
        str(h.range * 4), str(round(h.reload / combat.NORMAL * 20)), str(combat.BLAST["HOUFNICE"] * 4)]
    for name in ("HEAVY_ROCKET_CART", "ROCKET_CART"):                  # then the minimum range (#1350)
        assert combat.range_command("u", name, 4).split()[5] == str(combat.BLAST[name] * 4), name
