"""Bracer (#1503): the blacksmith researches it in the Imperial Age after Bodkin Arrow, in its slot. Archers and the
buildings that shoot get more attack and range, the town center more attack only, as Fletching and Bodkin Arrow."""
from menu_line import item
from test_forging import menus
from test_forging import setup as smith
from test_tower_fletching import CASTLE, TC, TOWER, values
from test_tower_fletching import setup as towers

from game import combat, train

SMITH = (11, 3)                                                    # a block cell of the blacksmith


def text(g, name, building=None):
    """The cost and time text of the menu item of name, from the data (as train.show writes it)."""
    return (" · ".join(f"{v} {r}" for r, v in train.price(g, name, building).items()) or "free") + \
        f" · {round(train.seconds(g, name, building), 1):g} s · "


def test_bracer_is_in_the_slot_of_bodkin_arrow_in_the_imperial_age():
    server, g = smith(food=1000)
    g.stock.update(gold=1000)
    g.techs |= {"CASTLE_AGE", "FLETCHING", "BODKIN_ARROW"}
    train.open_menu(g, "Steve", SMITH)
    assert ":Bracer:" not in menus(server)[-1]                        # the Castle Age
    g.techs.add("IMPERIAL_AGE")
    train.open_menu(g, "Steve", SMITH)
    assert item(menus(server)[-1], "Bracer").endswith(":Bracer:" + text(g, "BRACER") + "research")
    g.techs.discard("BODKIN_ARROW")
    train.open_menu(g, "Steve", SMITH)
    assert ":Bracer:" not in menus(server)[-1]                        # not before Bodkin Arrow
    g.techs.add("BODKIN_ARROW")
    assert train.queue(g, "Steve", SMITH, "BRACER")
    train.tick(g, train.TRAIN_TIMES["BRACER"])
    assert "BRACER" in g.techs


def test_archers_get_attack_and_range():
    server, g = smith()
    before = train.stats(g, "ARCHER")
    train.research(g, {"name": "BRACER", "player": "Steve"})
    after = train.stats(g, "ARCHER")
    assert after.attack > before.attack and after.range > before.range
    assert combat.stats_command("a", "ARCHER", after) in server.log   # the live archer
    assert train.stats(g, "MILITIA") == combat.stats("MILITIA")


def test_the_buildings_that_shoot_get_the_values_of_bracer():
    server, g = towers()
    for t in ("FLETCHING", "BODKIN_ARROW"):
        train.research(g, {"name": t, "player": "Steve"})
    before = {r: values(server, r) for r in (TC, CASTLE, TOWER)}
    train.research(g, {"name": "BRACER", "player": "Steve"})
    after = {r: values(server, r) for r in before}
    (hp, attack, reach), (hp0, attack0, reach0) = after[TC], before[TC]
    assert hp == hp0 and attack > attack0 and reach == reach0          # the town center: attack only
    for r in (CASTLE, TOWER):
        assert after[r][0] == before[r][0] and after[r][1] > before[r][1] and after[r][2] > before[r][2], r
