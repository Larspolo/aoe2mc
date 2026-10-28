"""game/train.py: the siege workshop trains the rocket cart in the Castle Age and upgrades it to the heavy rocket cart in
the Imperial Age (#2140, AoE2 DE wiki infobox "Rocket Cart" revision 1084676: 135 wood, 155 gold, 40 s; UpCost 800 wood,
600 gold, UpTime 75 s): only the Chinese, Jurchens, Khitans and Koreans, in place of the mangonel line."""
from test_forging import menus
from test_siege_upgrades import WORKSHOP, research, setup

import units
from game import civs, combat, train

OWN = {"CHINESE", "JURCHENS", "KHITANS", "KOREANS"}


def player(civ):
    server, g = setup()
    g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    g.sites.append({"name": "HOUSE", "player": 1, "footprint": [20, 22, 20, 22], "done": True})   # room for new units
    return server, g


def test_the_values_are_those_of_the_wiki():
    assert len(train.HELP["ROCKET_CART"]) <= 50
    r, h = combat.stats("ROCKET_CART"), combat.stats("HEAVY_ROCKET_CART")
    assert (r.hp, r.pierce, r.range, h.hp, h.pierce, h.range) == (45, 6, 7, 65, 8, 8)
    assert units.siege("ROCKET_CART") and units.siege("HEAVY_ROCKET_CART")


def test_a_korean_player_sees_the_rocket_cart_and_not_the_mangonel():
    server, g = player("KOREANS")
    train.open_menu(g, "Steve", WORKSHOP)
    menu = menus(server)[-1] + " "
    assert " 20:firework_rocket:Rocket Cart:135 wood · 155 gold · 40 s · queue 0/15 " in menu
    assert " 21:book:Heavy Rocket Cart:800 wood · 600 gold · 75 s · research " in menu
    assert "Mangonel" not in menu and "Onager" not in menu
    assert train.queue(g, "Steve", WORKSHOP, "MANGONEL") is None


def test_a_briton_player_sees_the_mangonel_and_not_the_rocket_cart():
    server, g = player("BRITONS")
    train.open_menu(g, "Steve", WORKSHOP)
    menu = menus(server)[-1] + " "
    assert " 1:dispenser:Mangonel:" in menu and " 4:book:Onager:" in menu and "Rocket Cart" not in menu
    assert train.queue(g, "Steve", WORKSHOP, "ROCKET_CART") is None
    assert train.queue(g, "Steve", WORKSHOP, "HEAVY_ROCKET_CART_UPGRADE") is None


def test_the_upgrade_changes_live_and_new_rocket_carts():
    server, g = player("CHINESE")
    assert train.queue(g, "Steve", WORKSHOP, "ROCKET_CART")
    uuid, = train.tick(g, 40)
    summon, = [c for c in server.log if c.startswith("summon")]
    assert summon.startswith("summon minecraft:minecart ") and g.soldiers[uuid] == "ROCKET_CART"
    research(g, WORKSHOP, "HEAVY_ROCKET_CART_UPGRADE")
    assert g.soldiers[uuid] == "HEAVY_ROCKET_CART"
    assert combat.stats_command(uuid, "HEAVY_ROCKET_CART", train.stats(g, "HEAVY_ROCKET_CART")) in server.log
    assert "HEAVY_ROCKET_CART" in train.trains(g, "SIEGE_WORKSHOP")
    train.open_menu(g, "Steve", WORKSHOP)
    assert " 20:firework_rocket:Heavy Rocket Cart:" in menus(server)[-1]
    assert train.queue(g, "Steve", WORKSHOP, "HEAVY_ROCKET_CART")
    new, = train.tick(g, 40)
    assert g.soldiers[new] == "HEAVY_ROCKET_CART"


def test_the_civilizations_of_the_wiki():
    every = set().union(*civs.MISSING.values())
    for name in ("ROCKET_CART", "HEAVY_ROCKET_CART_UPGRADE"):
        assert every - set(civs.MISSING[name]) == OWN, name
    for name in ("MANGONEL", "ONAGER_UPGRADE", "SIEGE_ONAGER_UPGRADE"):
        assert set(civs.MISSING[name]) == OWN, name
