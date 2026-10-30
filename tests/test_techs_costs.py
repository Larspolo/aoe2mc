"""The key "costs" of a technology changes the cost of a group of units (Kshatriyas, Szlachta Privileges, #4225).
Test data: monkeypatched train.BY_KEY lines, not the values of the data lines (owner, 2026-10-29, #4242)."""
import train as plain_train  # civs.cost imports train by its plain name (not game.train)
from test_train_castle import setup

from game import civs


def test_a_researched_technology_changes_the_cost_of_its_group_only(monkeypatch):
    monkeypatch.setitem(plain_train.BY_KEY["costs"], "TEST_FOOD", [["military units", "food", 0.75]])
    monkeypatch.setitem(plain_train.BY_KEY["costs"], "TEST_GOLD", [[["KNIGHT"], "gold", 0.4]])
    server, g = setup("BRITONS")
    before = {n: plain_train.price(g, n) for n in ("MILITIA", "VILLAGER_MALE", "KNIGHT")}
    g.techs.add("TEST_FOOD")
    assert plain_train.price(g, "MILITIA")["food"] == int(before["MILITIA"]["food"] * 0.75 + 0.5)
    assert plain_train.price(g, "VILLAGER_MALE") == before["VILLAGER_MALE"]
    g.techs.add("TEST_GOLD")
    assert plain_train.price(g, "KNIGHT")["gold"] == int(before["KNIGHT"]["gold"] * 0.4 + 0.5)
    assert plain_train.price(g, "MILITIA")["gold"] == before["MILITIA"]["gold"]


RES = ("food", "wood", "gold", "stone")


def test_each_costs_line_has_the_form_of_a_cost_rule():
    for t, rules in plain_train.BY_KEY["costs"].items():
        for what, r, c in rules:
            assert (isinstance(what, list) or what in civs.GROUPS or what.endswith(" technologies")) and all(k in RES for k in (r or "food").split(">")), t
            assert isinstance(c, float), t
