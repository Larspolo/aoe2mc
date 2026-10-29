"""The unique technologies of the Bulgarians (#4098): Stirrups (Castle Age, 400 food, 200 gold, 35 s: the cavalry
reloads 33 % faster) and Bagains (Imperial Age, 900 food, 450 gold, 40 s: +5 melee armor of the Two-Handed Swordsman
line). The values are those of the AoE2 DE wiki ("Unique technology"). Only the Bulgarians have them."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def test_only_the_castle_of_the_bulgarians_researches_stirrups():
    server, g = setup("BULGARIANS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'STIRRUPS')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "STIRRUPS") is None


def test_only_the_castle_of_the_bulgarians_researches_bagains():
    server, g = setup("BULGARIANS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'BAGAINS')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "BAGAINS") is None


def test_stirrups_reload_cavalry_33_percent_faster_and_keep_infantry():
    server, g = setup("BULGARIANS", food=3000, wood=3000, gold=3000, ages=2)
    knight = train.stats(g, "KNIGHT")
    militia = train.stats(g, "MILITIA")
    assert train.queue(g, "Steve", CASTLE, "STIRRUPS")
    train.tick(g, train.seconds(g, "STIRRUPS", "CASTLE"))
    assert "STIRRUPS" in g.techs
    assert train.stats(g, "KNIGHT").reload < knight.reload
    assert train.stats(g, "MILITIA").reload == militia.reload          # not cavalry


def test_bagains_add_melee_armor_to_the_two_handed_swordsmen_only():
    server, g = setup("BULGARIANS", food=3000, wood=3000, gold=3000, ages=3)
    champion = train.stats(g, "CHAMPION")
    man_at_arms = train.stats(g, "MAN_AT_ARMS")
    assert train.queue(g, "Steve", CASTLE, "BAGAINS")
    train.tick(g, train.seconds(g, "BAGAINS", "CASTLE"))
    assert "BAGAINS" in g.techs
    assert train.stats(g, "CHAMPION").melee > champion.melee
    assert train.stats(g, "MAN_AT_ARMS").melee == man_at_arms.melee    # not a Two-Handed Swordsman
