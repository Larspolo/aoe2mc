"""Plumed Archer (#1887): the castle of the Mayans trains the Plumed Archer (with the Mayan cost bonus of each age) and
researches Elite Plumed Archer in the Imperial Age, with the values of the AoE2 DE wiki (the data). The upgrade changes
the live and the new units."""
from menu_line import item
from test_train_castle import menus, setup

import buildings
from game import combat, train

CASTLE = (12, 4)
CIV = min(set(buildings.CIV_TO_ARCH) - set(train.civs.MISSING["PLUMED_ARCHER"]))   # the Mayans
UPGRADE = "ELITE_PLUMED_ARCHER_UPGRADE"


def cost(g, name):
    """The cost text of a menu item: the price with the bonus of the civilization."""
    return " · ".join(f"{v} {r}" for r, v in train.price(g, name, "CASTLE").items())


def test_the_castle_of_the_mayans_trains_the_plumed_archer():
    server, g = setup(CIV, food=0, wood=1000, gold=1000)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    unit = item(menu, "Plumed Archer")                                    # the Mayan bonus, Castle Age
    assert unit.startswith(f"{train.SLOTS['PLUMED_ARCHER']}:") and f":{cost(g, 'PLUMED_ARCHER')} · " in unit
    assert unit.endswith("queue 0/15") and "Elite Plumed" not in menu     # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, train.SLOTS["PLUMED_ARCHER"]) == 1
    assert g.queues[rect][0]["name"] == "PLUMED_ARCHER"
    server, g = setup(min(train.civs.MISSING["PLUMED_ARCHER"]), ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Plumed" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    assert CIV not in train.civs.MISSING[UPGRADE]
    server, g = setup(CIV, food=5000, wood=5000, gold=5000, ages=3)
    g.soldiers["pa"] = "PLUMED_ARCHER"
    g.game.entities.setdefault("pa", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    up = item(menus(server)[-1], "Elite Plumed Archer")
    assert up.startswith(f"{train.SLOTS[UPGRADE]}:") and up.endswith(" · research")
    assert train.queue(g, "Steve", CASTLE, UPGRADE)
    train.tick(g, train.seconds(g, UPGRADE, "CASTLE"))
    assert UPGRADE in g.techs and g.soldiers["pa"] == "ELITE_PLUMED_ARCHER"
    assert combat.stats_command("pa", "ELITE_PLUMED_ARCHER") in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    unit = item(menu, "Elite Plumed Archer")                             # one item: the unit, no upgrade
    assert unit.startswith(f"{train.SLOTS['PLUMED_ARCHER']}:") and unit.endswith("queue 0/15")
    assert f":{cost(g, 'ELITE_PLUMED_ARCHER')} · " in unit                 # the Imperial Age bonus
    assert ":Plumed Archer:" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_PLUMED_ARCHER")
    assert train.queue(g, "Steve", CASTLE, "PLUMED_ARCHER") is None
