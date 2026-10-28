"""game/train.py: the siege workshop trains the flaming camel in the Imperial Age (#2190, AoE2 DE wiki infobox
"Flaming Camel", MediaWiki API, 2026-10-27: 75 food, 30 gold, 30 s, 55 HP, 20 attack, speed 1.3, sight 4): only the
Tatars."""
from test_bombard_cannon import setup
from test_loom import menus

from game import civs, train

build = train.build
SLOT = 19                                                              # the item row, after the traction trebuchet


def menu(civ):
    server, g = setup()
    g.stock["food"] = 1000
    g.data["players"] = {"1": {"civ": civ}}
    train.open_menu(g, "Steve", (3, 3))
    return server, g, menus(server)[-1]


def test_the_values_are_those_of_the_wiki():
    assert build.AGE["FLAMING_CAMEL"] == 3 and "FLAMING_CAMEL" not in build.NEEDS
    assert len(train.HELP["FLAMING_CAMEL"]) <= 50
    assert train.ITEMS["FLAMING_CAMEL"][0] == SLOT


def test_the_tatars_see_it():
    server, g, text = menu("TATARS")
    assert f"{SLOT}:fire_charge:Flaming Camel:75 food · 30 gold · 30 s · queue 0/15" in text
    assert train.queue(g, "Steve", (3, 3), "FLAMING_CAMEL")
    assert g.stock["food"] == 1000 - 75 and g.stock["gold"] == 1000 - 30


def test_the_franks_do_not_see_it():
    server, g, text = menu("FRANKS")
    assert "Flaming Camel" not in text
    assert not train.queue(g, "Steve", (3, 3), "FLAMING_CAMEL") and g.stock["food"] == 1000


def test_it_is_gray_before_the_imperial_age():
    server, g = setup(ages=2)
    assert build.locked(g, "FLAMING_CAMEL") == "Needs the Imperial Age"


def test_only_the_tatars_have_it():
    have = set().union(*civs.MISSING.values()) - set(civs.MISSING["FLAMING_CAMEL"])
    assert have == {"TATARS"}
