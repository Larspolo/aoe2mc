"""game/combat.py: the War Elephant has the AoE2 DE bonus against buildings (#1015)."""
from game import combat


def test_war_elephant_bonus_of_the_wiki():
    # The AoE2 wiki infobox "War Elephant (Age of Empires II)" of 2026-10-26: +30 vs All Buildings.
    assert combat.stats("WAR_ELEPHANT").bonus == {"building": 30}
    assert combat.damage("WAR_ELEPHANT", "HOUSE") == 15 - 0 + 30
