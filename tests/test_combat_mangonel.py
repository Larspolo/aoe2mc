"""game/combat.py: the Mangonel line hits with melee damage from its range, as in AoE2 (#1013)."""
from game import combat


def test_the_onager_hits_the_melee_armor_of_a_ram():
    assert combat.damage("ONAGER", "BATTERING_RAM") == 55 + 3 + 12   # melee armor -3, siege bonus 12 (pierce 180: 1 + 12)


def test_the_mangonel_line_has_range_kind_2():
    for name in ("MANGONEL", "ONAGER", "SIEGE_ONAGER"):
        assert combat.stats_command("u", name).split()[7] == "2", name
