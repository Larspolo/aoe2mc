"""game/train.py: the siege workshop trains the traction trebuchet in the Imperial Age (#2141, AoE2 DE wiki infobox
"Traction Trebuchet (Age of Empires II)", MediaWiki API, 2026-10-27): only the Shu, Wei and
Wu, in place of the bombard cannon. It needs no Chemistry and does not pack."""
from test_bombard_cannon import setup
from test_loom import menus

from game import train

build = train.build
LABEL = train.ITEMS["TRACTION_TREBUCHET"][2]


def menu(civ):
    server, g = setup(techs=["CHEMISTRY"])
    g.data["players"] = {"1": {"civ": civ}}
    train.open_menu(g, "Steve", (3, 3))
    return server, g, menus(server)[-1]


def test_the_wei_see_it_and_not_the_bombard_cannon():
    server, g, text = menu("WEI")
    assert f":{LABEL}:" in text
    assert train.ITEMS["BOMBARD_CANNON"][2] not in text and not train.queue(g, "Steve", (3, 3), "BOMBARD_CANNON")
    cost = train.price(g, "TRACTION_TREBUCHET")
    assert train.queue(g, "Steve", (3, 3), "TRACTION_TREBUCHET")
    assert g.stock["wood"] == 1000 - cost.get("wood", 0) and g.stock["gold"] == 1000 - cost.get("gold", 0)


def test_the_turks_see_the_bombard_cannon_and_not_it():
    server, g, text = menu("TURKS")
    assert train.ITEMS["BOMBARD_CANNON"][2] in text and LABEL not in text
    assert not train.queue(g, "Steve", (3, 3), "TRACTION_TREBUCHET") and g.stock["wood"] == 1000


def test_it_is_gray_before_the_imperial_age():
    server, g = setup(ages=2)
    assert build.locked(g, "TRACTION_TREBUCHET") == "Needs the Imperial Age"

