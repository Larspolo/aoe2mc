"""game/train.py: the siege workshop trains the mounted trebuchet in the Imperial Age (#2191, AoE2 DE wiki "Mounted
Trebuchet"): only the Khitans. It is a camel unit and does not pack, so units.classify makes a camel with the trebuchet
crew, not the minecart of the other trebuchets."""
from menu_line import item
from test_bombard_cannon import setup
from test_loom import menus

import buildings
import units
from game import combat, train

build = train.build
WITH = min(set(buildings.CIV_TO_ARCH) - set(train.civs.MISSING["MOUNTED_TREBUCHET"]))   # the Khitans


def menu(civ):
    server, g = setup(techs=["CHEMISTRY"])
    g.data["players"] = {"1": {"civ": civ}}
    train.open_menu(g, "Steve", (3, 3))
    return server, g, menus(server)[-1]


def test_the_khitans_see_it():
    server, g, text = menu(WITH)
    assert item(text, "Mounted Trebuchet").startswith(f"{train.SLOTS['MOUNTED_TREBUCHET']}:")
    food, gold, cost = g.stock["food"], g.stock["gold"], train.COSTS["MOUNTED_TREBUCHET"]
    assert "Traction Trebuchet" not in text and train.queue(g, "Steve", (3, 3), "MOUNTED_TREBUCHET")
    assert (g.stock["food"], g.stock["gold"]) == (food - cost.get("food", 0), gold - cost.get("gold", 0))


def test_the_franks_do_not_see_it():
    server, g, text = menu(min(train.civs.MISSING["MOUNTED_TREBUCHET"]))
    food = g.stock["food"]
    assert "Mounted Trebuchet" not in text
    assert not train.queue(g, "Steve", (3, 3), "MOUNTED_TREBUCHET") and g.stock["food"] == food


def test_it_is_gray_before_the_imperial_age():
    server, g = setup(ages=2)
    assert build.locked(g, "MOUNTED_TREBUCHET") == "Needs the Imperial Age"


def test_its_bonus_against_siege():
    mangonel = combat.stats("MANGONEL")
    assert combat.damage("MOUNTED_TREBUCHET", "MANGONEL") > \
        combat.damage("MOUNTED_TREBUCHET", "X", t=mangonel._replace(classes=()))   # the bonus of the siege class


def test_it_looks_like_a_camel_with_the_trebuchet_crew():
    e = units.classify("MOUNTED_TREBUCHET")
    assert e["id"] == "minecraft:camel" and e["Passengers"][0]["id"] == "minecraft:warden"
