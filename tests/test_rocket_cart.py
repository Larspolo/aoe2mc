"""game/train.py: the siege workshop trains the rocket cart in the Castle Age and upgrades it to the heavy rocket cart in
the Imperial Age (#2140, AoE2 DE wiki infobox "Rocket Cart"): only the civilizations of the data (civs.MISSING), in
place of the mangonel line."""
import re

from test_forging import menus
from test_siege_upgrades import WORKSHOP, research, setup

import units
from game import civs, combat, train

OWN = sorted(set().union(*civs.MISSING.values()) - set(civs.MISSING["ROCKET_CART"]))   # the civilizations of the cart
OTHER = next(c for c in sorted(civs.MISSING["ROCKET_CART"]) if c not in civs.MISSING["MANGONEL"])   # one with mangonels


def item(menu, name, kind):
    """True when the menu has the item `name` that ends with `kind` ("queue" or "research")."""
    return re.search(rf" \d+:\w+:{name}:[^:]* {kind}", menu) is not None


def player(civ):
    server, g = setup()
    g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    g.sites.append({"name": "HOUSE", "player": 1, "footprint": [20, 22, 20, 22], "done": True})   # room for new units
    return server, g


def test_the_help_is_short_and_the_carts_are_siege():
    assert len(train.HELP["ROCKET_CART"]) <= 50
    assert units.siege("ROCKET_CART") and units.siege("HEAVY_ROCKET_CART")


def test_a_player_of_the_cart_sees_the_rocket_cart_and_not_the_mangonel():
    server, g = player(OWN[0])
    train.open_menu(g, "Steve", WORKSHOP)
    menu = menus(server)[-1] + " "
    assert item(menu, "Rocket Cart", "queue") and item(menu, "Heavy Rocket Cart", "research")
    assert "Mangonel" not in menu and "Onager" not in menu
    assert train.queue(g, "Steve", WORKSHOP, "MANGONEL") is None


def test_another_player_sees_the_mangonel_and_not_the_rocket_cart():
    server, g = player(OTHER)
    train.open_menu(g, "Steve", WORKSHOP)
    menu = menus(server)[-1] + " "
    assert ":Mangonel:" in menu and "Rocket Cart" not in menu
    assert train.queue(g, "Steve", WORKSHOP, "ROCKET_CART") is None
    assert train.queue(g, "Steve", WORKSHOP, "HEAVY_ROCKET_CART_UPGRADE") is None


def test_the_upgrade_changes_live_and_new_rocket_carts():
    server, g = player(OWN[0])
    assert train.queue(g, "Steve", WORKSHOP, "ROCKET_CART")
    uuid, = train.tick(g, train.seconds(g, "ROCKET_CART"))
    summon, = [c for c in server.log if c.startswith("summon")]
    assert summon.startswith("summon minecraft:minecart ") and g.soldiers[uuid] == "ROCKET_CART"
    research(g, WORKSHOP, "HEAVY_ROCKET_CART_UPGRADE")
    assert g.soldiers[uuid] == "HEAVY_ROCKET_CART"
    assert combat.stats_command(uuid, "HEAVY_ROCKET_CART", train.stats(g, "HEAVY_ROCKET_CART")) in server.log
    assert "HEAVY_ROCKET_CART" in train.trains(g, "SIEGE_WORKSHOP")
    train.open_menu(g, "Steve", WORKSHOP)
    assert item(menus(server)[-1] + " ", "Heavy Rocket Cart", "queue")
    assert train.queue(g, "Steve", WORKSHOP, "HEAVY_ROCKET_CART")
    new, = train.tick(g, train.seconds(g, "HEAVY_ROCKET_CART"))
    assert g.soldiers[new] == "HEAVY_ROCKET_CART"
