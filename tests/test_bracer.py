"""Bracer (#1503): the blacksmith researches it in the Imperial Age after Bodkin Arrow, in its slot (AoE2 DE wiki
"Bracer": 300 food, 200 gold, 40 s). Archers and the buildings that shoot +1 attack and +1 range, the town center +1
attack only, as Fletching and Bodkin Arrow. Not for the civilizations without it in the wiki availability chart."""
from test_forging import menus
from test_forging import setup as smith
from test_tower_fletching import CASTLE, TC, TOWER, values
from test_tower_fletching import setup as towers

from game import civs, combat, train

SMITH = (11, 3)                                                    # a block cell of the blacksmith


def test_the_values_are_those_of_aoe2():
    assert train.TECH_AGE["BRACER"] == 3 and train.AFTER["BRACER"] == "BODKIN_ARROW"
    assert "BRACER" in train.TRAINS["BLACKSMITH"] and "BRACER" in civs.SMITH
    assert set(civs.MISSING["BRACER"]) == {"CELTS", "CUMANS", "FRANKS", "MALIANS", "MAPUCHE", "PERSIANS", "ROMANS",
                                           "SLAVS", "TEUTONS"}
    assert len(train.HELP["BRACER"]) <= 50


def test_bracer_is_in_the_slot_of_bodkin_arrow_in_the_imperial_age():
    server, g = smith(food=1000)
    g.stock.update(gold=1000)
    g.techs |= {"CASTLE_AGE", "FLETCHING", "BODKIN_ARROW"}
    train.open_menu(g, "Steve", SMITH)
    assert ":Bracer:" not in menus(server)[-1]                        # the Castle Age
    g.techs.add("IMPERIAL_AGE")
    train.open_menu(g, "Steve", SMITH)
    assert " 2:book:Bracer:300 food · 200 gold · 40 s · research " in menus(server)[-1] + " "
    g.techs.discard("BODKIN_ARROW")
    train.open_menu(g, "Steve", SMITH)
    assert ":Bracer:" not in menus(server)[-1]                        # not before Bodkin Arrow
    g.techs.add("BODKIN_ARROW")
    assert train.queue(g, "Steve", SMITH, "BRACER")
    train.tick(g, 40)
    assert "BRACER" in g.techs


def test_archers_get_one_attack_and_one_range():
    server, g = smith()
    before = train.stats(g, "ARCHER")
    train.research(g, {"name": "BRACER", "player": "Steve"})
    after = train.stats(g, "ARCHER")
    assert (after.attack, after.range) == (before.attack + 1, before.range + 1)
    assert combat.stats_command("a", "ARCHER", after) in server.log   # the live archer
    assert train.stats(g, "MILITIA") == combat.stats("MILITIA")


def test_the_buildings_that_shoot_get_the_values_of_bracer():
    server, g = towers()
    for t in ("FLETCHING", "BODKIN_ARROW", "BRACER"):
        train.research(g, {"name": t, "player": "Steve"})
    assert values(server, TC) == (2400, 8, 6)                        # +1 attack, the same range
    assert values(server, CASTLE) == (4800, 14, 11)
    assert values(server, TOWER) == (1020, 8, 11)
