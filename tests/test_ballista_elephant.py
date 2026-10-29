"""Ballista Elephant (#1752): the castle of the Khmer trains the Ballista Elephant and researches Elite Ballista
Elephant in the Imperial Age. The upgrade changes the live and the new units."""
from menu_line import item
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def text(g, name, building=None):
    """The cost and time text of the menu item of name, from the data (as train.show writes it)."""
    return (" · ".join(f"{v} {r}" for r, v in train.price(g, name, building).items()) or "free") + \
        f" · {round(train.seconds(g, name, building), 1):g} s · "


def test_the_castle_of_the_khmer_trains_the_ballista_elephant():
    server, g = setup("KHMER", food=0, wood=0, gold=0)
    g.stock.update(train.price(g, "BALLISTA_ELEPHANT", "CASTLE"))
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert item(menu, "Ballista Elephant").endswith(":Ballista Elephant:" + text(g, "BALLISTA_ELEPHANT", "CASTLE") + "queue 0/15")
    assert "Elite Ballista Elephant" not in menu                                 # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "BALLISTA_ELEPHANT"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Ballista Elephant" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("KHMER", food=2000, wood=2000, gold=2000, ages=3)
    g.soldiers["ub"] = "BALLISTA_ELEPHANT"
    g.game.entities.setdefault("ub", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    up = item(menus(server)[-1], "Elite Ballista Elephant")
    assert up.endswith(":Elite Ballista Elephant:" + text(g, "ELITE_BALLISTA_ELEPHANT_UPGRADE", "CASTLE") + "research")
    assert train.queue(g, "Steve", CASTLE, "ELITE_BALLISTA_ELEPHANT_UPGRADE")
    train.tick(g, train.seconds(g, "ELITE_BALLISTA_ELEPHANT_UPGRADE", "CASTLE"))
    assert "ELITE_BALLISTA_ELEPHANT_UPGRADE" in g.techs and g.soldiers["ub"] == "ELITE_BALLISTA_ELEPHANT"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert item(menu, "Elite Ballista Elephant").endswith(":Elite Ballista Elephant:" +
                                                          text(g, "ELITE_BALLISTA_ELEPHANT", "CASTLE") + "queue 0/15")
    assert ":Ballista Elephant:" not in menu.replace("Elite Ballista Elephant", "") and up not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_BALLISTA_ELEPHANT")
    assert train.queue(g, "Steve", CASTLE, "BALLISTA_ELEPHANT") is None
