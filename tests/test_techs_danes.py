"""The code of the factor of a bonus ("bonus_times") with test data: Northmen's Fury of the Danes (#4259). The test
data is the effect of the data line of the technology, so that the test does not fail when a value changes."""
import math

from game import combat, train

EFFECT = [{"if": [{"forms": ["MANGONEL"]}, {"names": ["CATAPULT_GALLEON"]}], "add": {"range": 1}},
          {"if": [{"class": "siege"}, {"names": ["CATAPULT_GALLEON"]}], "bonus_times": {"building": 1.4}}]
UNITS = ("ONAGER", "CATAPULT_GALLEON", "TREBUCHET", "KNIGHT")


def changed():
    before = {n: combat.stats(n)._replace(range=5, bonus={"building": 33}) for n in UNITS}   # test values (#5398)
    change = train.effect(EFFECT)
    return before, {n: change(n, s) for n, s in before.items()}


def test_the_factor_of_a_bonus_applies_to_siege_and_the_range_to_the_mangonel_line():
    before, after = changed()
    assert after["ONAGER"].range == before["ONAGER"].range + 1
    assert after["CATAPULT_GALLEON"].range == before["CATAPULT_GALLEON"].range + 1
    assert after["TREBUCHET"].range == before["TREBUCHET"].range
    assert after["ONAGER"].bonus["building"] == math.floor(before["ONAGER"].bonus["building"] * 1.4 + 0.5)
    assert after["CATAPULT_GALLEON"].bonus["building"] == math.floor(before["CATAPULT_GALLEON"].bonus["building"] * 1.4 + 0.5)
    assert after["TREBUCHET"].bonus["building"] == math.floor(before["TREBUCHET"].bonus["building"] * 1.4 + 0.5)


def test_a_unit_outside_the_tests_keeps_its_values():
    before, after = changed()
    assert after["KNIGHT"] == before["KNIGHT"]
