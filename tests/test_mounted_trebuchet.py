"""game/train.py: the siege workshop trains the mounted trebuchet in the Imperial Age (#2191, AoE2 DE wiki "Mounted
Trebuchet", MediaWiki API, 2026-10-27: 175 food, 175 gold, 46 s): only the Khitans. It is a camel unit and does not
pack, so units.classify makes a camel with the trebuchet crew, not the minecart of the other trebuchets."""
from test_bombard_cannon import setup
from test_loom import menus

import units
from game import civs, combat, train

build = train.build
UNIT = 18                                                              # the item row under the queue row


def menu(civ):
    server, g = setup(techs=["CHEMISTRY"])
    g.data["players"] = {"1": {"civ": civ}}
    train.open_menu(g, "Steve", (3, 3))
    return server, g, menus(server)[-1]


def test_the_values_are_those_of_the_wiki():
    assert "MOUNTED_TREBUCHET" not in build.NEEDS and len(train.HELP["MOUNTED_TREBUCHET"]) <= 50
    assert train.ITEMS["MOUNTED_TREBUCHET"][0] == UNIT


def test_the_khitans_see_it():
    server, g, text = menu("KHITANS")
    assert f"{UNIT}:camel_spawn_egg:Mounted Trebuchet:" in text
    food, gold, cost = g.stock["food"], g.stock["gold"], train.COSTS["MOUNTED_TREBUCHET"]
    assert "Traction Trebuchet" not in text and train.queue(g, "Steve", (3, 3), "MOUNTED_TREBUCHET")
    assert (g.stock["food"], g.stock["gold"]) == (food - cost["food"], gold - cost["gold"])


def test_the_franks_do_not_see_it():
    server, g, text = menu("FRANKS")
    food = g.stock["food"]
    assert "Mounted Trebuchet" not in text
    assert not train.queue(g, "Steve", (3, 3), "MOUNTED_TREBUCHET") and g.stock["food"] == food


def test_it_is_gray_before_the_imperial_age():
    server, g = setup(ages=2)
    assert build.locked(g, "MOUNTED_TREBUCHET") == "Needs the Imperial Age"


def test_only_the_khitans_have_it():
    assert set().union(*civs.MISSING.values()) - set(civs.MISSING["MOUNTED_TREBUCHET"]) == {"KHITANS"}


def test_its_bonus_against_siege():
    melee = combat.stats("MANGONEL").melee
    assert combat.damage("MOUNTED_TREBUCHET", "MANGONEL") == 30 - melee + 30
    assert combat.damage("MOUNTED_TREBUCHET", "MILITIA") == 30 - combat.stats("MILITIA").melee


def test_it_looks_like_a_camel_with_the_trebuchet_crew():
    e = units.classify("MOUNTED_TREBUCHET")
    assert e["id"] == "minecraft:camel" and e["Passengers"][0]["id"] == "minecraft:warden"
