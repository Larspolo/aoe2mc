"""game/train.py: the siege workshop trains the traction trebuchet in the Imperial Age (#2141, AoE2 DE wiki infobox
"Traction Trebuchet (Age of Empires II)", MediaWiki API, 2026-10-27: 175 wood, 210 gold, 70 s): only the Shu, Wei and
Wu, in place of the bombard cannon. It needs no Chemistry and does not pack."""
from test_bombard_cannon import setup
from test_loom import menus

from game import civs, train

build = train.build
UNIT = 18                                                              # the item row under the queue row


def menu(civ):
    server, g = setup(techs=["CHEMISTRY"])
    g.data["players"] = {"1": {"civ": civ}}
    train.open_menu(g, "Steve", (3, 3))
    return server, g, menus(server)[-1]


def test_the_values_are_those_of_the_wiki():
    assert build.AGE["TRACTION_TREBUCHET"] == 3
    assert "TRACTION_TREBUCHET" not in build.NEEDS and len(train.HELP["TRACTION_TREBUCHET"]) <= 50
    assert train.ITEMS["TRACTION_TREBUCHET"][0] == UNIT


def test_the_wei_see_it_and_not_the_bombard_cannon():
    server, g, text = menu("WEI")
    assert f"{UNIT}:chest_minecart:Traction Trebuchet:131 wood · 158 gold · 70 s · queue 0/15" in text   # -25 % (#2246)
    assert "Bombard Cannon" not in text and not train.queue(g, "Steve", (3, 3), "BOMBARD_CANNON")
    assert train.queue(g, "Steve", (3, 3), "TRACTION_TREBUCHET")
    assert g.stock["wood"] == 1000 - 131 and g.stock["gold"] == 1000 - 158


def test_the_turks_see_the_bombard_cannon_and_not_it():
    server, g, text = menu("TURKS")
    assert "Bombard Cannon" in text and "Traction Trebuchet" not in text
    assert not train.queue(g, "Steve", (3, 3), "TRACTION_TREBUCHET") and g.stock["wood"] == 1000


def test_it_is_gray_before_the_imperial_age():
    server, g = setup(ages=2)
    assert build.locked(g, "TRACTION_TREBUCHET") == "Needs the Imperial Age"


def test_the_civilizations_of_the_wiki():
    have = set().union(*civs.MISSING.values()) - set(civs.MISSING["TRACTION_TREBUCHET"])
    assert have == {"SHU", "WEI", "WU"} <= set(civs.MISSING["BOMBARD_CANNON"])
