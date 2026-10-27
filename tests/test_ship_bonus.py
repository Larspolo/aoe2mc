"""game/combat.py: the arrows of the towers, the castle, the town center and the dock have the AoE2 DE attack against
the class "Ships" (#1564, the "Attack bonus" field of the wiki infobox of each building). Ships have 0 armor in that
class, so the bonus adds to the pierce attack: a watch tower does 5 - 3 + 5 = 7 to a galley."""
from test_heated_shot import hit
from test_tower_upgrades import setup

from game import build, combat

SHIPS = {"BOMBARD_TOWER": 40, "CASTLE": 11, "DOCK": 3, "FORTIFIED_TOWER": 12, "GUARD_TOWER": 7, "KEEP": 8, "KREPOST": 10,
         "TOWN_CENTER": 5, "WATCH_TOWER": 5}


def test_each_building_that_shoots_has_its_aoe2_attack_against_ships():
    assert {k: s.bonus.get(combat.SHIP) for k, s in combat.BUILDINGS.items() if combat.SHIP in s.bonus} == SHIPS
    assert all(s.bonus.get(combat.SHIP) for k, s in combat.BUILDINGS.items() if s.attack)


def test_a_watch_tower_arrow_does_7_to_a_galley_and_13_after_heated_shot():
    _, g = setup(2)
    galley = combat.stats("GALLEY")
    assert hit(build.values(g, "WATCH_TOWER"), galley) == 7
    g.techs.add("HEATED_SHOT")
    assert hit(build.values(g, "WATCH_TOWER"), galley) == 13
    assert hit(build.values(g, "WATCH_TOWER"), combat.stats("MILITIA")) == 5 - 1   # not against land units
    assert combat.damage("WATCH_TOWER", "GALLEY") == 7
