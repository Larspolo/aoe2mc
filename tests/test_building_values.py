"""Each building of the build menu has a row in combat.BUILDINGS (#1403): a blacksmith had the 40 hit
points of DEFAULT and no class "building", so a trebuchet did 200 to it, not 450."""
from game import build, combat


def test_each_building_of_the_build_menu_has_a_row():
    # walls and gates: combat.WALLS; a farm has no target (its farmers stand on it), a fish trap not yet (#1438:
    # combat.building_box takes the ground next to it, and the open water has none)
    names = {n for n in build.COSTS if n not in combat.WALLS and n not in ("FARM", "FISH_TRAP")}
    assert names - set(combat.BUILDINGS) == set()
    assert all("building" in combat.BUILDINGS[n].classes for n in names)


def test_a_trebuchet_gets_its_building_bonus_against_a_blacksmith():
    a = combat.stats("TREBUCHET")._replace(attack=200, bonus={"building": 250})   # test values (#5398)
    t = combat.stats("BLACKSMITH")._replace(pierce=7)
    assert combat.damage("TREBUCHET", "BLACKSMITH", a=a, t=t) == 200 - 7 + 250   # the bonus vs. buildings
