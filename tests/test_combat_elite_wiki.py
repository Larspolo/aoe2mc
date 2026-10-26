"""The elite unique units of game/combat.py have the base values of their AoE2 wiki infobox (#1075): DE, no upgrades,
no civilization bonus (the infobox shows some values with the bonus and names the base value in a tooltip), as the
base units (#1041)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import combat  # noqa: E402
from combat import ARC  # noqa: E402

S = combat.STATS


def test_the_eight_units_of_the_ticket():
    assert S["ELITE_BERSERK"].hp == 62                                  # 74 with the Viking bonus
    assert (S["ELITE_GENOESE_CROSSBOWMAN"].melee, S["ELITE_GENOESE_CROSSBOWMAN"].pierce) == (1, 0)   # Italian bonus
    assert S["ELITE_HUSKARL"].bonus == {ARC: 10, "building": 3}         # +6 vs buildings with the Goth bonus
    assert S["ELITE_JANISSARY"].hp == 40                                # 50 with the Turkish bonus
    assert S["ELITE_MANGUDAI"].reload == 2.1                            # 1.68 with the Mongol bonus
    assert S["ELITE_RATTAN_ARCHER"].hp == 40                            # 48 with the Vietnamese bonus
    assert S["ELITE_SAMURAI"].reload == 1.9                             # 1.43 with the Japanese bonus
    assert S["ELITE_KONNIK"].bonus == {}                                # the infobox lists no bonus


def test_the_elite_mameluke_has_its_base_hit_points():
    assert (S["MAMELUKE"].hp, S["ELITE_MAMELUKE"].hp) == (80, 90)       # 100 and 113 with the Saracen bonus


def test_an_elite_unit_is_never_weaker_than_its_base_unit():
    for name, s in S.items():
        if name.startswith("ELITE_") and (b := S.get(name.removeprefix("ELITE_"))):
            assert s.hp >= b.hp and s.attack >= b.attack and s.reload <= b.reload, name
