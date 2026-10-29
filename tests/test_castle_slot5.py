"""The elite upgrades of all unique units share castle slot 5, and each civ sees and orders only its own (#1720)."""
from test_train_castle import menus, setup
from test_train_knight import clashes

from game import train

CASTLE = (12, 4)
OTHER = "ELITE_TEST_UPGRADE"                                       # a second elite upgrade, of the Britons only
SLOT, _, LABEL = train.ITEMS["ELITE_CHAKRAM_THROWER_UPGRADE"]     # the slot of all elite upgrades


def other(monkeypatch, first=True):
    """Put OTHER into castle slot 5, before or after the elite upgrade of the Gurjaras."""
    gurjaras = [n for n in train.TRAINS["CASTLE"] if n != "ELITE_CHAKRAM_THROWER_UPGRADE"]
    castle = (OTHER, "ELITE_CHAKRAM_THROWER_UPGRADE") if first else ("ELITE_CHAKRAM_THROWER_UPGRADE", OTHER)
    monkeypatch.setitem(train.TRAINS, "CASTLE", tuple(gurjaras) + castle)
    monkeypatch.setitem(train.ITEMS, OTHER, (SLOT, "book", "Elite Test"))
    monkeypatch.setitem(train.COSTS, OTHER, {"food": 1})
    monkeypatch.setitem(train.TRAIN_TIMES, OTHER, 1)
    monkeypatch.setitem(train.BY_KEY["age"], OTHER, 3)
    monkeypatch.setitem(train.civs.MISSING, OTHER, tuple(sorted(set().union(*train.civs.MISSING.values()) - {"BRITONS"})))


def test_two_civs_share_slot_5(monkeypatch):
    other(monkeypatch)
    names = train.TRAINS["CASTLE"]
    assert clashes(names, "BRITONS") == clashes(names, "GURJARAS") == []
    monkeypatch.setitem(train.civs.MISSING, OTHER, ())             # now the Gurjaras see two items in slot 5
    assert clashes(names, "GURJARAS") == [SLOT]


def test_the_click_orders_the_upgrade_of_the_own_civ(monkeypatch):
    for first in (True, False):
        other(monkeypatch, first)
        server, g = setup("GURJARAS", food=2000, wood=0, gold=2000, ages=3)
        rect = train.open_menu(g, "Steve", CASTLE)
        menu = menus(server)[-1] + " "
        assert f" {SLOT}:book:{LABEL}:" in menu and "Elite Test" not in menu
        assert train.order(g, "Steve", rect, SLOT) == 1 and g.queues[rect][0]["name"] == "ELITE_CHAKRAM_THROWER_UPGRADE"
        server, g = setup("BRITONS", food=2000, wood=0, gold=2000, ages=3)
        rect = train.open_menu(g, "Steve", CASTLE)
        assert f" {SLOT}:book:Elite Test:" in menus(server)[-1] + " " and "Chakram" not in menus(server)[-1]
        assert train.order(g, "Steve", rect, SLOT) == 1 and g.queues[rect][0]["name"] == OTHER
