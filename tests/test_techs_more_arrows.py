"""Unique technologies that add arrows (#4258): Yasama (the Japanese: towers fire 2 more arrows) and Tigui (the Malians:
Town Centers fire 8 more arrows, also with no garrison). The data of data/train.jsonl, key "more_arrows", with the
values of the AoE2 DE wiki ("Unique technology")."""
from test_train_castle import menus, setup

from game import garrison, train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def town_center(g):
    """The block rect of the own town center of setup()."""
    return next(r for r, o in garrison.holders(g).items() if o["name"] == "TOWN_CENTER")


def arrows(g, rect):
    """The number of arrows that the plugin command of the building rect sends."""
    return int(garrison.arrows_command(g, rect).split()[-1])


def test_yasama_is_in_the_castle_menu_of_the_japanese_only():
    server, g = setup("JAPANESE", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'YASAMA')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "YASAMA") is None


def test_tigui_is_in_the_castle_menu_of_the_malians_only():
    server, g = setup("MALIANS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'TIGUI')}:" in menus(server)[-1]
    server, g = setup("JAPANESE", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "TIGUI") is None


def test_tigui_adds_8_arrows_to_each_own_town_center():
    server, g = setup("MALIANS", food=3000, wood=3000, ages=2)
    rect, before = town_center(g), arrows(g, town_center(g))
    assert train.more_arrows(g, "TOWN_CENTER") == 0
    sent, command = [], g.command
    g.command = lambda c: (sent.append(c), command(c))[1]        # the commands of the research
    assert train.queue(g, "Steve", CASTLE, "TIGUI")
    train.tick(g, train.seconds(g, "TIGUI", "CASTLE"))
    assert "TIGUI" in g.techs
    assert arrows(g, rect) == before + 8
    assert garrison.arrows_command(g, rect) in sent


def test_yasama_adds_2_arrows_to_towers_and_keeps_the_base_of_the_others():
    server, g = setup("JAPANESE", food=3000, wood=3000, ages=2)
    base = garrison.arrows("WATCH_TOWER", [])
    assert train.more_arrows(g, "WATCH_TOWER") == 0
    assert train.queue(g, "Steve", CASTLE, "YASAMA")
    train.tick(g, train.seconds(g, "YASAMA", "CASTLE"))
    assert "YASAMA" in g.techs
    assert train.more_arrows(g, "WATCH_TOWER") == 2
    assert train.more_arrows(g, "TOWN_CENTER") == 0
    assert garrison.arrows("WATCH_TOWER", [], 1, train.more_arrows(g, "WATCH_TOWER")) == base + 2
    assert arrows(g, town_center(g)) == garrison.arrows("TOWN_CENTER", [], 1, 0)
