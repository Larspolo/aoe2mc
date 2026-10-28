"""The ship speed and reload bonuses of five civilizations (#2292, AoE2 DE): Berber ships move 10 % faster, Saracen
galleys and Byzantine fire ships and dromons attack 25 % faster, Varangian longships and catapult galleons 15 % faster,
the Chinese fire galley line and fire lancers move 5 %/10 % faster in the Castle/Imperial Age."""
import pytest

from game import civs, combat, fleet, train

from test_civ_work import setup

AGES = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def player(civ, age=0):
    g = setup(civ)
    g.techs.update(AGES[:age])
    return g


def test_berber_ships_sail_10_percent_faster():
    for name in ("GALLEY", "FISHING_SHIP", "TRADE_COG"):
        assert fleet.speed(name, 4, player("BERBERS")) == pytest.approx(fleet.speed(name, 4, player("BRITONS")) * 1.1)


@pytest.mark.parametrize("civ, names", [("SARACENS", ("GALLEY", "WAR_GALLEY", "GALLEON")),
                                        ("BYZANTINES", ("FIRE_GALLEY", "FIRE_SHIP", "FAST_FIRE_SHIP", "DROMON")),
                                        ("VARANGIANS", ("LONGSHIP", "ELITE_LONGSHIP", "CATAPULT_GALLEON"))])
def test_the_ships_of_the_bonus_attack_faster(civ, names):
    factor = 1.15 if civ == "VARANGIANS" else 1.25
    for name in names:
        base = combat.stats(name).reload
        assert train.stats(player(civ), name).reload == pytest.approx(base / factor, abs=0.001), name
        assert train.stats(player("BRITONS"), name).reload == base, name


def test_other_ships_keep_their_reload():
    for civ, name in (("SARACENS", "FIRE_SHIP"), ("BYZANTINES", "GALLEY"), ("VARANGIANS", "GALLEY")):
        assert train.stats(player(civ), name).reload == combat.stats(name).reload, (civ, name)
    assert "SARACENS" in civs.MISSING["DROMON"]                      # the Saracen rule names the dromons too


def test_the_chinese_fire_galley_line_and_fire_lancers_move_faster_from_the_castle_age():
    for name in ("FIRE_GALLEY", "FIRE_SHIP", "FAST_FIRE_SHIP", "FIRE_LANCER", "ELITE_FIRE_LANCER"):
        assert [civs.speed(player("CHINESE", a), name) for a in range(4)] == pytest.approx([1, 1, 1.05, 1.1]), name
    assert fleet.speed("FIRE_SHIP", 4, player("CHINESE", 3)) == pytest.approx(fleet.speed("FIRE_SHIP", 4) * 1.1)
    assert civs.speed(player("CHINESE", 3), "GALLEY") == 1
