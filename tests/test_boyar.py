"""Boyar (#1721): the castle of the Slavs trains the boyar and researches Elite Boyar in the Imperial Age. The
upgrade changes the live and the new units."""
from menu_line import item
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def text(g, name, building=None):
    """The cost and time text of the menu item of name, from the data (as train.show writes it)."""
    return (" · ".join(f"{v} {r}" for r, v in train.price(g, name, building).items()) or "free") + \
        f" · {round(train.seconds(g, name, building), 1):g} s · "


def test_the_castle_of_the_slavs_trains_the_boyar():
    server, g = setup("SLAVS", food=0, wood=0, gold=0)
    g.stock.update(train.price(g, "BOYAR", "CASTLE"))
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert item(menu, "Boyar").endswith(":Boyar:" + text(g, "BOYAR", "CASTLE") + "queue 0/15")
    assert "Elite Boyar" not in menu                                   # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "BOYAR"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Boyar" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("SLAVS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["by"] = "BOYAR"
    g.game.entities.setdefault("by", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    up = item(menus(server)[-1], "Elite Boyar")
    assert up.endswith(":Elite Boyar:" + text(g, "ELITE_BOYAR_UPGRADE", "CASTLE") + "research")
    assert train.queue(g, "Steve", CASTLE, "ELITE_BOYAR_UPGRADE")
    train.tick(g, train.seconds(g, "ELITE_BOYAR_UPGRADE", "CASTLE"))
    assert "ELITE_BOYAR_UPGRADE" in g.techs and g.soldiers["by"] == "ELITE_BOYAR"
    assert combat.stats_command("by", "ELITE_BOYAR") in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert item(menu, "Elite Boyar").endswith(":Elite Boyar:" + text(g, "ELITE_BOYAR", "CASTLE") + "queue 0/15")
    assert ":Boyar:" not in menu and up not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_BOYAR")
    assert train.queue(g, "Steve", CASTLE, "BOYAR") is None
