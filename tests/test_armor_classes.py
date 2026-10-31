"""The AoE2 DE armor classes of units (#5240): a bonus against a class, and the technologies that select units by
class (AoE2 selects them by unit class, so an armor class alone gives no technology)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import civs  # noqa: E402
import combat  # noqa: E402
import train  # noqa: E402

BASE = combat.Stats(hp=50, attack=4, melee=0, pierce=0, range=0, reload=2.0, bonus={}, classes=("infantry",))


def test_a_bonus_against_a_new_class_adds_its_damage():
    attacker = BASE._replace(bonus={"eagle": 8})
    eagle = BASE._replace(classes=("infantry", "eagle"))
    assert combat.damage("A", "T", attacker, eagle) - combat.damage("A", "T", attacker, BASE) == 8


def test_a_monk_with_the_cavalry_armor_class_gets_no_cavalry_technology():
    monk = BASE._replace(classes=("cavalry", "unique", "monk"))
    knight = BASE._replace(classes=("cavalry",))
    assert train.test({"class": "cavalry"}, "X", knight) and not train.test({"class": "cavalry"}, "X", monk)
    assert train.test({"class": "monk"}, "X", monk)
    assert train.barding("X", knight) and not train.barding("X", monk)
    assert train.melee("X", knight) and not train.melee("X", monk)
    assert civs.mounted(knight) and not civs.mounted(monk)


def test_cavalry_but_elephants():
    assert train.cavalry_but_elephants("X", BASE._replace(classes=("cavalry",)))
    assert not train.cavalry_but_elephants("X", BASE._replace(classes=("cavalry", "elephant")))


def test_trade_and_transport_ships_are_no_warships():
    ship = BASE._replace(classes=("ship",))
    assert civs.GROUPS["warships"]("GALLEY", ship)
    assert not civs.GROUPS["warships"]("TRADE_COG", ship._replace(attack=0))   # a ship with no attack
