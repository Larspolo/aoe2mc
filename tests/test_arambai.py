"""Arambai (#1751): the castle of the Burmese trains the Arambai and researches Elite Arambai in the Imperial Age. The
upgrade changes the live
and the new units."""
from menu_line import item
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def text(g, name, building):
    """The cost and time text of the menu item of name, from the data (as train.show writes it)."""
    return " · ".join(f"{v} {r}" for r, v in train.price(g, name, building).items()) + \
        f" · {round(train.seconds(g, name, building), 1):g} s · "


def test_the_castle_of_the_burmese_trains_the_arambai():
    server, g = setup("BURMESE", wood=75, gold=60)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert item(menu, "Arambai").endswith(":Arambai:" + text(g, "ARAMBAI", "CASTLE") + "queue 0/15")
    assert "Elite Arambai" not in menu                                 # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "ARAMBAI"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Arambai" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("BURMESE", food=2000, wood=75, gold=2000, ages=3)
    g.soldiers["ar"] = "ARAMBAI"
    g.game.entities.setdefault("ar", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    up = item(menus(server)[-1], "Elite Arambai")
    assert up.endswith(":Elite Arambai:" + text(g, "ELITE_ARAMBAI_UPGRADE", "CASTLE") + "research")
    assert train.queue(g, "Steve", CASTLE, "ELITE_ARAMBAI_UPGRADE")
    train.tick(g, train.seconds(g, "ELITE_ARAMBAI_UPGRADE", "CASTLE"))
    assert "ELITE_ARAMBAI_UPGRADE" in g.techs and g.soldiers["ar"] == "ELITE_ARAMBAI"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert item(menu, "Elite Arambai").endswith(":Elite Arambai:" + text(g, "ELITE_ARAMBAI", "CASTLE") + "queue 0/15")
    assert ":Arambai:" not in menu and up not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_ARAMBAI")
    assert train.queue(g, "Steve", CASTLE, "ARAMBAI") is None
