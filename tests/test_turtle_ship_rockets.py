"""The Turtle Ship line fires 3 rockets each 2.0 AoE2 seconds, as in the AoE2 DE data (#5241): one shot of the unit
and a volley of 2 extra projectiles (combat.VOLLEY), pierce damage (no MELEE_RANGED)."""
from test_armenian_volley import summoned

from game import combat

NAMES = ("TURTLE_SHIP", "ELITE_TURTLE_SHIP")


def test_a_turtle_ship_shoots_pierce_shots_at_its_reload():
    for name in NAMES:
        s = combat.stats(name)
        cmd = combat.stats_command("u", name).split()
        assert name not in combat.MELEE_RANGED and cmd[7] == "1", name          # kind 1: ranged, pierce damage
        assert cmd[-1] == str(round(s.reload / combat.NORMAL * 20)), name


def test_each_shot_of_a_turtle_ship_has_two_extra_rockets():
    for name in NAMES:
        v = combat.VOLLEY[name]
        uuid, log = summoned("KOREANS", name)
        assert f"aoe volley {uuid} {v['shots']} {v['attack']}" in log, name
