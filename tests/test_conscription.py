"""Conscription (#1455): the castle researches it in the Imperial Age (150 food, 150 gold, 60 s, AoE2 wiki
"Conscription (Age of Empires II)"), and then the barracks, archery range, stable and castle train their units 33 %
faster; the siege workshop and the technologies do not change."""
from test_train_castle import menus, setup

from game import train

WORKSHOP = {"kind": "building", "name": "SIEGE_WORKSHOP", "player": 1, "tile": [18.0, 12.0], "footprint": [16, 10, 20, 14]}


def test_the_values_are_those_of_aoe2():
    assert train.COSTS["CONSCRIPTION"] == {"food": 150, "gold": 150} and train.TRAIN_TIMES["CONSCRIPTION"] == 60
    assert train.TECH_AGE["CONSCRIPTION"] == 3 and len(train.HELP["CONSCRIPTION"]) <= 50
    assert set(train.CONSCRIPT[0]) == {"ARCHERY_RANGE", "BARRACKS", "CASTLE", "STABLE"} and train.CONSCRIPT[1] == 1.33


def test_the_castle_researches_it_only_in_the_imperial_age():
    server, g = setup(food=150, gold=150)
    train.open_menu(g, "Steve", (12, 4))
    assert "Conscription" not in menus(server)[-1]
    server, g = setup(food=150, gold=150, ages=3)
    rect = train.open_menu(g, "Steve", (12, 4))
    assert " 2:book:Conscription:150 food · 150 gold · 60 s" in menus(server)[-1]
    assert train.order(g, "Steve", rect, 2) == 1 and g.stock["food"] == g.stock["gold"] == 0
    train.tick(g, 59.9)
    assert "CONSCRIPTION" not in g.techs                               # a technology: not faster
    train.tick(g, 0.2)
    assert "CONSCRIPTION" in g.techs


def takes(g, rect, seconds):
    """True when the queue of rect is still busy 0.1 s before seconds and empty 0.1 s after them."""
    train.tick(g, seconds - 0.1)
    busy = bool(g.queues[rect])
    train.tick(g, 0.2)
    return busy and not g.queues[rect]


def test_after_it_the_castle_trains_33_percent_faster_and_the_siege_workshop_not():
    server, g = setup(wood=1000, gold=1000, ages=3)
    g.data["objects"].append(dict(WORKSHOP))
    castle, shop, t = (10, 14, 2, 6), (16, 20, 10, 14), train.TRAIN_TIMES["LONGBOWMAN"]
    assert train.queue(g, "Steve", (12, 4), "LONGBOWMAN") and takes(g, castle, t)
    g.techs.add("CONSCRIPTION")
    assert train.queue(g, "Steve", (12, 4), "LONGBOWMAN") and takes(g, castle, t / 1.33)
    assert train.queue(g, "Steve", (18, 12), "BATTERING_RAM") and takes(g, shop, train.TRAIN_TIMES["BATTERING_RAM"])
