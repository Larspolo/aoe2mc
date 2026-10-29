"""A new unique unit needs only the alphabetical table lines: the castle and the civ rule come from UNIQUE (#1760)."""
from test_train_castle import menus, setup
from test_train_knight import clashes

from game import train

CASTLE = (12, 4)
NEW = "TEST_UNIT"


def add(monkeypatch):
    """A unique unit of the Slavs with only the table lines of a ticket (#1721): no TRAINS and no civs.MISSING line."""
    monkeypatch.setitem(train.UNIQUE, "SLAVS", NEW)
    for name, cost, time in ((NEW, {"food": 1}, 1), ("ELITE_" + NEW, {"food": 1}, 1), (f"ELITE_{NEW}_UPGRADE", {"food": 2}, 2)):
        monkeypatch.setitem(train.COSTS, name, cost)
        monkeypatch.setitem(train.TRAIN_TIMES, name, time)
    monkeypatch.setitem(train.ITEMS, NEW, (0, "horse_spawn_egg", "Test Unit"))
    monkeypatch.setitem(train.ITEMS, "ELITE_" + NEW, (0, "horse_spawn_egg", "Elite Test Unit"))
    monkeypatch.setitem(train.ITEMS, f"ELITE_{NEW}_UPGRADE", (5, "book", "Elite Test Unit"))
    monkeypatch.setitem(train.BY_KEY["age"], f"ELITE_{NEW}_UPGRADE", 3)
    monkeypatch.setitem(train.TECHS, f"ELITE_{NEW}_UPGRADE", lambda name, s: s)
    monkeypatch.setitem(train.UPGRADES, f"ELITE_{NEW}_UPGRADE", (NEW, "ELITE_" + NEW))
    monkeypatch.setattr(train.civs, "MISSING", train.civs.MISSING | train.own_civ_only())   # as at the import


def test_the_castle_of_the_own_civ_trains_it_and_its_elite_upgrade(monkeypatch):
    add(monkeypatch)
    assert "BRITONS" in train.civs.MISSING[f"ELITE_{NEW}_UPGRADE"] and "SLAVS" not in train.civs.MISSING[NEW]
    server, g = setup("SLAVS", food=100, wood=0, gold=0, ages=3)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:horse_spawn_egg:Test Unit:" in menu and " 5:book:Elite Test Unit:" in menu
    assert train.order(g, "Steve", rect, 5) == 1 and g.queues[rect][0]["name"] == f"ELITE_{NEW}_UPGRADE"
    server, g = setup("GURJARAS", food=2000, wood=0, gold=2000, ages=3)
    train.open_menu(g, "Steve", CASTLE)
    slot, item, label = train.ITEMS[f"ELITE_{train.UNIQUE['GURJARAS']}_UPGRADE"]   # the own elite upgrade
    assert "Test Unit" not in menus(server)[-1] and f" {slot}:{item}:{label}:" in menus(server)[-1] + " "


def test_no_civ_sees_two_items_in_a_slot(monkeypatch):
    add(monkeypatch)
    names = train.TRAINS["CASTLE"] + tuple(f"ELITE_{u}_UPGRADE" for u in train.UNIQUE.values()
                                           if f"ELITE_{u}_UPGRADE" in train.COSTS)
    for civ in ("SLAVS", "GURJARAS", "BRITONS"):
        assert clashes(names, civ) == []
