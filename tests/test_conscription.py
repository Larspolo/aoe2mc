"""Conscription (#1455): the castle researches it in the Imperial Age (AoE2 wiki "Conscription (Age of Empires II)"),
and then the buildings of train.CONSCRIPT (the castle too) train their units faster; the siege workshop and the
technologies do not change."""
from test_castle_upgrades import entry
from test_train_castle import menus, setup

from game import train

WORKSHOP = {"kind": "building", "name": "SIEGE_WORKSHOP", "player": 1, "tile": [18.0, 12.0], "footprint": [16, 10, 20, 14]}


def test_the_help_text_is_short():
    assert len(train.HELP["CONSCRIPTION"]) <= 50


def test_the_castle_researches_it_only_in_the_imperial_age():
    server, g = setup(food=150, gold=150)
    train.open_menu(g, "Steve", (12, 4))
    assert "Conscription" not in menus(server)[-1]
    server, g = setup(food=10000, gold=10000, ages=3)
    rect = train.open_menu(g, "Steve", (12, 4))
    assert " " + entry(g, (12, 4), "CONSCRIPTION") in menus(server)[-1]
    cost = train.price(g, "CONSCRIPTION")
    assert train.order(g, "Steve", rect, train.layout(g, rect)["CONSCRIPTION"][0]) == 1
    assert (g.stock["food"], g.stock["gold"]) == (10000 - cost.get("food", 0), 10000 - cost.get("gold", 0))
    train.tick(g, train.TRAIN_TIMES["CONSCRIPTION"] - 0.1)
    assert "CONSCRIPTION" not in g.techs                               # a technology: not faster
    train.tick(g, 0.2)
    assert "CONSCRIPTION" in g.techs


def takes(g, rect, seconds):
    """True when the queue of rect is still busy 0.1 s before seconds and empty 0.1 s after them."""
    train.tick(g, seconds - 0.1)
    busy = bool(g.queues[rect])
    train.tick(g, 0.2)
    return busy and not g.queues[rect]


def test_after_it_the_castle_trains_faster_and_the_siege_workshop_not():
    server, g = setup(wood=1000, gold=1000, ages=3)
    g.data["objects"].append(dict(WORKSHOP))
    castle, shop, t = (10, 14, 2, 6), (16, 20, 10, 14), train.TRAIN_TIMES["LONGBOWMAN"]
    assert train.queue(g, "Steve", (12, 4), "LONGBOWMAN") and takes(g, castle, t)
    g.techs.add("CONSCRIPTION")
    assert train.queue(g, "Steve", (12, 4), "LONGBOWMAN") and takes(g, castle, t / train.CONSCRIPT[1])
    assert train.queue(g, "Steve", (18, 12), "BATTERING_RAM") and takes(g, shop, train.TRAIN_TIMES["BATTERING_RAM"])
