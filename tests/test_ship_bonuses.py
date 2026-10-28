"""The hit point and armor bonuses of the ships of five civilizations (#2290, AoE2 DE): Portuguese ships +10 % hit points,
Saxon longships and catapult galleons +20 %, Roman galley line and dromons +1/+1 armor, Japanese fishing ships double
hit points and +2 pierce armor, Saracen transport ships double hit points."""
from game import combat, train

from test_civ_work import setup


def test_the_ships_of_five_civilizations_get_their_bonuses():
    for civ, name, field, factor, add in (("PORTUGUESE", "GALLEY", "hp", 1.1, 0), ("PORTUGUESE", "FISHING_SHIP", "hp", 1.1, 0),
                                          ("SAXONS", "LONGSHIP", "hp", 1.2, 0), ("SAXONS", "CATAPULT_GALLEON", "hp", 1.2, 0),
                                          ("ROMANS", "WAR_GALLEY", "melee", 1, 1), ("ROMANS", "DROMON", "pierce", 1, 1),
                                          ("JAPANESE", "FISHING_SHIP", "hp", 2, 0), ("JAPANESE", "FISHING_SHIP", "pierce", 1, 2),
                                          ("SARACENS", "TRANSPORT_SHIP", "hp", 2, 0)):
        base = getattr(combat.stats(name), field)
        assert getattr(train.stats(setup(civ), name), field) == round(base * factor) + add, (civ, name, field)
        assert getattr(train.stats(setup("BRITONS"), name), field) == base, (name, field)


def test_other_units_keep_their_values():
    for civ, name in (("SAXONS", "GALLEY"), ("ROMANS", "FIRE_GALLEY"), ("JAPANESE", "GALLEY"), ("SARACENS", "FISHING_SHIP"),
                      ("PORTUGUESE", "KNIGHT")):
        assert train.stats(setup(civ), name) == combat.stats(name), (civ, name)


def test_a_trained_portuguese_galley_gets_the_hit_points_on_the_server():
    from test_civ_units import trained
    _, uuid, log = trained("PORTUGUESE", "GALLEY")
    assert f"aoe stats {uuid} {round(combat.stats('GALLEY').hp * 1.1)} " in " ".join(log)
