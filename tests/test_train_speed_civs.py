"""The train rate bonuses of the civilizations (#1927, civs.TRAIN_RATE, AoE2 DE wiki): the Aztecs create all military
units faster; the Khitans train and upgrade skirmishers, genitours and the spearman and scout lines faster.
train.seconds divides the time by civs.train_rate."""
import types

import pytest

from game import civs, combat, train


def player(civ, ages=("FEUDAL_AGE",)):
    return types.SimpleNamespace(data={"players": {"1": {"civ": civ}}}, player=1, techs=set(ages))


def test_an_aztec_military_unit_trains_faster():
    for name, building in (("MILITIA", "BARRACKS"), ("KNIGHT", "STABLE")):
        assert train.seconds(player("AZTECS"), name, building) < train.TRAIN_TIMES[name], name
    assert train.seconds(player("BRITONS"), "MILITIA", "BARRACKS") == train.TRAIN_TIMES["MILITIA"]


@pytest.mark.parametrize("name", ["VILLAGER_MALE", "FISHING_SHIP", "TRADE_CART", "MONK", "MAN_AT_ARMS_UPGRADE", "LOOM"])
def test_the_aztecs_keep_the_time_of_civilians_and_technologies(name):
    assert train.seconds(player("AZTECS"), name) == train.TRAIN_TIMES[name]


@pytest.mark.parametrize("name", ["SKIRMISHER", "ELITE_SKIRMISHER_UPGRADE", "SPEARMAN", "PIKEMAN_UPGRADE",
                                  "HALBERDIER_UPGRADE", "SCOUT_CAVALRY", "LIGHT_CAVALRY_UPGRADE", "HUSSAR_UPGRADE",
                                  "IMPERIAL_SKIRMISHER_UPGRADE"])
def test_a_khitan_unit_of_the_lines_and_its_upgrade_take_less_time(name):
    assert train.seconds(player("KHITANS"), name) < train.TRAIN_TIMES[name]
    assert train.seconds(player("FRANKS"), name) == train.TRAIN_TIMES[name]


@pytest.mark.parametrize("name", ["VILLAGER_MALE", "MILITIA", "ARCHER", "KNIGHT", "MAN_AT_ARMS_UPGRADE", "LOOM"])
def test_the_khitans_keep_the_time_of_the_other_units(name):
    assert train.seconds(player("KHITANS"), name) == train.TRAIN_TIMES[name]


def test_the_genitour_group_has_the_genitour_line():
    group = civs.GROUPS["skirmishers, genitours, spearman and scout lines"]
    for name in ("GENITOUR", "ELITE_GENITOUR", "HALBERDIER", "HUSSAR", "WINGED_HUSSAR", "IMPERIAL_SKIRMISHER"):
        assert group(name, combat.stats(name)), name
    assert not group("ARCHER", combat.stats("ARCHER"))
