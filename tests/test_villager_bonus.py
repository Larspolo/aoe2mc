"""game/combat.py: the villager has the AoE2 DE attack bonuses (wiki infobox "AttackBonus"): +3 against all buildings,
+6 against the stone defense (combat.STONE: the stone walls and gates and the towers, not the castle and not the
palisades) and +6 against heavy siege (#1590)."""
from test_arson import hit

from game import combat

V = combat.stats("VILLAGER_MALE")


def test_a_villager_hits_with_the_aoe2_damage():
    assert hit(V, combat.stats("HOUSE")) == 3 + 3                        # attack 3, melee armor 0
    assert hit(V, combat.wall("STONE_WALL", 1)) == 0 + 3 + 6             # melee armor 8
    assert hit(V, combat.wall("GATE", 1)) == 0 + 3 + 6
    assert hit(V, combat.wall("PALISADE_WALL", 1)) == 1 + 3              # melee armor 2: no stone defense
    assert hit(V, combat.stats("WATCH_TOWER")) == 2 + 3 + 6              # melee armor 1
    assert hit(V, combat.stats("CASTLE")) == 0 + 3                       # melee armor 8: the class Castles
    assert hit(V, combat.stats("HUSSITE_WAGON")) == 3 + 6                # melee armor 0, heavy siege
    assert hit(V, combat.stats("MILITIA")) == 3


def test_the_stone_defense_class_and_the_building_command():
    stone = {k for k, s in combat.BUILDINGS.items() if combat.STONE in s.classes}
    assert stone == {"BOMBARD_TOWER", "FORTIFIED_TOWER", "GUARD_TOWER", "KEEP", "WATCH_TOWER"}
    assert {k for k in combat.WALLS if combat.STONE in combat.wall(k, 0).classes} == \
        {"FORTIFIED_GATE", "FORTIFIED_WALL", "GATE", "STONE_WALL"}
    cmd = combat.building(combat.target_uuid([0, 0, 2, 2]), "WATCH_TOWER", 1, (0, 64, 0, 1, 70, 1), 4)[-1]
    assert cmd.endswith(" building,standard,stone")                     # the plugin reads the classes
    house = combat.building(combat.target_uuid([4, 4, 6, 6]), "HOUSE", 1, (0, 64, 0, 1, 70, 1), 4)[-1]
    assert house.split()[-1] == "1"                                     # the default classes: no class text


def test_other_units_do_not_change():
    assert combat.stats("MILITIA").bonus == {} and combat.stats("TRADE_CART").bonus == {}
    assert combat.damage("MILITIA", "HOUSE") == 4 and combat.damage("MILITIA", "WATCH_TOWER") == 3   # 4 - 1
