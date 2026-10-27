"""War Chariot (#2142): the Shu train the war chariot at the siege workshop from the Castle Age (75 food, 90 gold,
32 s), in place of the scorpion line, with the values of the AoE2 DE wiki infobox "War Chariot (Age of Empires II)".
It has no elite upgrade. The game program leaves out the barrage mode: it shoots the focus fire bolt."""
from test_loom import menus
from test_siege_train import setup

import units
from game import build, civs, combat, replay, train


def workshop(civ, ages=3):
    server, g = setup(ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.stock.update(food=1000)
    train.open_menu(g, "Steve", (3, 3))
    return server, g, menus(server)[-1] + " "


def test_the_values_are_those_of_aoe2():
    assert (train.COSTS["WAR_CHARIOT"], train.TRAIN_TIMES["WAR_CHARIOT"]) == ({"food": 75, "gold": 90}, 32)
    assert build.AGE["WAR_CHARIOT"] == 2 and len(train.HELP["WAR_CHARIOT"]) <= 50
    s = combat.STATS["WAR_CHARIOT"]
    assert (s.hp, s.attack, s.melee, s.pierce, s.range, s.reload) == (65, 8, 0, 5, 6, 6.5)
    assert s.bonus == {"building": 2} and {"cavalry", "siege", "unique"} <= set(s.classes)
    assert combat.MIN_RANGE["WAR_CHARIOT"] == 1 and combat.sight("WAR_CHARIOT") == 8 and replay.SPEEDS["WAR_CHARIOT"] == 0.9
    assert units.classify("WAR_CHARIOT")["id"] == "minecraft:minecart"   # a siege unit with a crew
    assert not [n for n, u in train.UPGRADES.items() if "WAR_CHARIOT" in str(u)]   # no elite upgrade


def test_only_the_shu_have_the_war_chariot_and_they_have_no_scorpion():
    assert set(civs.MISSING["WAR_CHARIOT"]) == {r["name"] for r in civs.ROWS} - {"SHU"}
    assert "SHU" in civs.MISSING["SCORPION"] and "SHU" in civs.MISSING["HEAVY_SCORPION_UPGRADE"]


def test_a_shu_player_sees_the_war_chariot_and_a_wu_player_the_scorpion():
    server, g, menu = workshop("SHU")
    assert " 2:bow:War Chariot:75 food · 90 gold · 32 s " in menu
    assert ":Scorpion:" not in menu and "Heavy Scorpion" not in menu
    assert train.queue(g, "Steve", (3, 3), "WAR_CHARIOT") == (2, 6, 2, 6)
    server, g, menu = workshop("WU")
    assert " 2:crossbow:Scorpion:75 wood · 75 gold · 30 s " in menu and "War Chariot" not in menu
    assert train.queue(g, "Steve", (3, 3), "WAR_CHARIOT") is None


def test_the_war_chariot_needs_the_castle_age():
    server, g, menu = workshop("SHU", ages=1)
    assert ":gray_dye:War Chariot:75 food · 90 gold · 32 s · Needs the Castle Age" in menu
