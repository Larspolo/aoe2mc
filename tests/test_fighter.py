"""Furious the Monkey Boy has no armor class, but attacks the enemies in its sight as a soldier (#1995): the key
"fighter" of its line in game/data/units.jsonl. The villager, the monk, the king and the trade units do not."""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(__file__), "..", "game")]
import combat  # noqa: E402


def test_furious_gets_a_line_of_sight():
    assert combat.sight_command("u", "FURIOUS_THE_MONKEY_BOY", 1)


def test_units_that_do_not_fight_get_none():
    assert all(combat.sight_command("u", n, 1) is None for n in ("VILLAGER", "MONK", "KING", "TRADE_CART", "PETARD"))


def test_each_fighter_has_an_attack_and_no_class():
    assert all(combat.STATS[n].attack and not combat.STATS[n].classes for n in combat.FIGHTERS)
