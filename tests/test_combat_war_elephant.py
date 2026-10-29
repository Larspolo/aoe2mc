"""game/combat.py: the War Elephant has the AoE2 DE bonus against buildings (#1015)."""
from game import combat


def test_war_elephant_has_a_bonus_against_buildings():
    t = combat.stats("HOUSE")
    assert combat.damage("WAR_ELEPHANT", "HOUSE") > combat.damage("WAR_ELEPHANT", "HOUSE", t=t._replace(classes=()))
