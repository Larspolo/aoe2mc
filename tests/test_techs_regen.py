"""Unique technologies with regeneration (#4255): the Dravidians research Medical Corps (elephants regenerate 30 HP per
minute) and the Berbers research Maghrebi Camels (camels 15 HP per minute), with the values of the AoE2 DE wiki
("Unique technology"). The rates are the key "regen" of data/train.jsonl."""
from test_train_castle import menus, setup

from game import civs, combat, train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def rate(g, name):
    """The hit points per AoE2 minute of unit name in the data of the player (civs.regen)."""
    return civs.regen(g, name, combat.stats(name))


def test_only_the_castle_of_the_dravidians_researches_medical_corps():
    server, g = setup("DRAVIDIANS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'MEDICAL_CORPS')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "MEDICAL_CORPS") is None


def test_only_the_castle_of_the_berbers_researches_maghrebi_camels():
    server, g = setup("BERBERS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'MAGHREBI_CAMELS')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "MAGHREBI_CAMELS") is None


def test_medical_corps_adds_regeneration_to_elephants_only():
    server, g = setup("DRAVIDIANS", food=3000, wood=3000, gold=3000, ages=2)
    elephant, knight = rate(g, "BATTLE_ELEPHANT"), rate(g, "KNIGHT")
    assert train.queue(g, "Steve", CASTLE, "MEDICAL_CORPS")
    train.tick(g, train.seconds(g, "MEDICAL_CORPS", "CASTLE"))
    assert "MEDICAL_CORPS" in g.techs
    assert rate(g, "BATTLE_ELEPHANT") == elephant + train.BY_KEY["regen"]["MEDICAL_CORPS"][1]
    assert rate(g, "KNIGHT") == knight                              # not an elephant


def test_maghrebi_camels_add_regeneration_to_camels_only():
    server, g = setup("BERBERS", food=3000, wood=3000, gold=3000, ages=3)
    camel, knight = rate(g, "CAMEL_RIDER"), rate(g, "KNIGHT")
    assert train.queue(g, "Steve", CASTLE, "MAGHREBI_CAMELS")
    train.tick(g, train.seconds(g, "MAGHREBI_CAMELS", "CASTLE"))
    assert "MAGHREBI_CAMELS" in g.techs
    assert rate(g, "CAMEL_RIDER") == camel + train.BY_KEY["regen"]["MAGHREBI_CAMELS"][1]
    assert rate(g, "KNIGHT") == knight                              # not a camel
