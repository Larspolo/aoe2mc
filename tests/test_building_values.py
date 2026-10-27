"""Each building of the build menu has its AoE2 DE values in combat.BUILDINGS (#1403): a blacksmith had the 40 hit
points of DEFAULT and no class "building", so a trebuchet did 200 to it, not 450."""
from game import build, combat


def test_each_building_of_the_build_menu_has_a_row():
    # walls and gates: combat.WALLS; a farm has no target (its farmers stand on it)
    names = {n for n in build.COSTS if n not in combat.WALLS and n != "FARM"}
    assert names - set(combat.BUILDINGS) == set()
    assert all("building" in combat.BUILDINGS[n].classes for n in names)


def test_the_new_rows_have_the_values_of_the_wiki():
    # (hit points, melee armor, pierce armor) of the first age of each building (AoE2 DE wiki infobox)
    assert {n: (s.hp, s.melee, s.pierce) for n, s in combat.BUILDINGS.items()
            if n in ("BLACKSMITH", "LUMBER_CAMP", "MILL", "MINING_CAMP", "UNIVERSITY")} == {
        "BLACKSMITH": (1800, 1, 8), "LUMBER_CAMP": (600, 0, 7), "MILL": (600, 0, 7), "MINING_CAMP": (600, 0, 7),
        "UNIVERSITY": (2100, 2, 9)}


def test_a_trebuchet_gets_its_building_bonus_against_a_blacksmith():
    assert combat.damage("TREBUCHET", "BLACKSMITH") > 400                # 200 + 250 vs. buildings - the armor
