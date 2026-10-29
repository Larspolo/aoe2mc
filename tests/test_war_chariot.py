"""War Chariot (#2142): the own civilization (game/data/civs.jsonl) trains the war chariot at the siege workshop from the
Castle Age, in place of the scorpion line, with the values of game/data/train.jsonl. The game program leaves out the
barrage mode: it shoots the focus fire bolt."""
from test_loom import menus
from test_siege_train import setup
from test_urumi_swordsman import item, label

from game import civs, train

ALL = {r["name"] for r in civs.ROWS}
OWN = sorted(ALL - set(civs.MISSING["WAR_CHARIOT"]))[0]
SCORPIONS = sorted(ALL - set(civs.MISSING["SCORPION"]) - {OWN})[0]   # a civilization with the scorpion


def workshop(civ, ages=3):
    server, g = setup(ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.stock.update(food=1000)
    train.open_menu(g, "Steve", (3, 3))
    return server, g, menus(server)[-1] + " "


def test_the_own_civ_sees_the_war_chariot_and_another_civ_the_scorpion():
    server, g, menu = workshop(OWN)
    assert item(g, "WAR_CHARIOT", "")[:-1] in menu
    assert f":{label('SCORPION')}:" not in menu and f":{label('HEAVY_SCORPION_UPGRADE')}:" not in menu
    assert train.queue(g, "Steve", (3, 3), "WAR_CHARIOT") == (2, 6, 2, 6)
    server, g, menu = workshop(SCORPIONS)
    assert item(g, "SCORPION", "")[:-1] in menu and f":{label('WAR_CHARIOT')}:" not in menu
    assert train.queue(g, "Steve", (3, 3), "WAR_CHARIOT") is None


def test_the_war_chariot_needs_the_castle_age():
    server, g, menu = workshop(OWN, ages=1)
    slot, kind, name = train.ITEMS["WAR_CHARIOT"]
    assert f":gray_dye:{name}:" in menu and "Needs the Castle Age" in menu
