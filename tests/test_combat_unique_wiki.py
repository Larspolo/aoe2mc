"""The base unique units of game/combat.py have the values of their AoE2 wiki infobox (#1041): DE, no upgrades, no
civilization bonus (the wiki shows some values with the bonus and names the base value in a tooltip)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import combat  # noqa: E402
from combat import ARC, SIE, SPE  # noqa: E402


def test_the_six_units_of_the_ticket():
    assert combat.STATS["BERSERK"].hp == 54                             # 65 with the Viking bonus
    j = combat.STATS["JANISSARY"]
    assert (j.hp, j.bonus) == (35, {SIE: 2})                            # 44 HP with the Turkish bonus; +2 vs rams
    assert combat.STATS["LONGBOWMAN"].bonus == {SPE: 2}
    assert combat.STATS["HUSKARL"].bonus == {ARC: 6, "building": 2}      # +4 vs buildings with the Goth bonus
    assert combat.STATS["MANGUDAI"].reload == 2.1                       # 1.68 with the Mongol bonus
    assert combat.STATS["SAMURAI"].reload == 1.9                        # 1.43 with the Japanese bonus


def test_the_other_base_values_without_a_civilization_bonus():
    g = combat.STATS["GENOESE_CROSSBOWMAN"]
    assert (g.melee, g.pierce) == (1, 0)                                # 2/1 with the Italian bonus
    assert combat.STATS["RATTAN_ARCHER"].hp == 35                       # 42 with the Vietnamese bonus
    assert combat.STATS["ELITE_TEUTONIC_KNIGHT"].melee == 8             # 10 with the Teuton bonus
    assert combat.STATS["KONNIK"].bonus == {}                           # the wiki lists no bonus
    assert combat.damage("JANISSARY", "BATTERING_RAM") == 2              # 180 pierce armor: only the bonus hits
