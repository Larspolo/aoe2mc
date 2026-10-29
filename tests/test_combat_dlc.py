"""The military units of the DLCs Dynasties of India, Return of Rome and The Three Kingdoms have values and a valid
command (#1009)."""
import re

from game import combat

UNITS = ("ARMORED_ELEPHANT", "FIRE_LANCER", "GRENADIER", "HEI_GUANG_CAVALRY", "IRON_PAGODA", "LEGIONARY",
         "ROCKET_CART", "SIEGE_ELEPHANT", "TRACTION_TREBUCHET", "WHITE_FEATHER_GUARD")


def test_each_unit_has_values_and_a_valid_command():
    for name in UNITS:
        assert name in combat.STATS, name
        cmd = combat.stats_command("u", name)
        assert re.fullmatch(r"aoe stats u \d+ \d+ -?\d+ \d+ [012] [a-z,]+ (-|[a-z]+:\d+(,[a-z]+:\d+)*) \d+", cmd), cmd
        assert (cmd.split()[7] == "2") == (name in combat.MELEE_RANGED), name   # melee damage from a range
