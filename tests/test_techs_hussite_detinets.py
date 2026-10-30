"""Hussite Reforms and Detinets (#4325): a resource "gold>food" of the key "costs" of a technology moves a part of one
resource of the cost to another (civs.cost). Test data: monkeypatched train.BY_KEY lines, not the values of the data
lines (owner, 2026-10-29, #4242)."""
from test_train_castle import setup

import build as plain_build          # civs.cost imports build and train by their plain names
import train as plain_train


def test_a_swap_moves_the_gold_of_monks_and_monastery_technologies_to_food(monkeypatch):
    monkeypatch.setitem(plain_train.BY_KEY["costs"], "TEST_SWAP",
                        [[["MONK"], "gold>food", 1.0], ["MONASTERY technologies", "gold>food", 1.0]])
    server, g = setup("BOHEMIANS")
    tech = next(t for t in plain_train.TRAINS["MONASTERY"] if t in plain_train.TECHS
                and plain_train.price(g, t).get("gold"))
    before = {n: plain_train.price(g, n) for n in ("MONK", tech, "MILITIA")}
    g.techs.add("TEST_SWAP")
    for n in ("MONK", tech):
        after = plain_train.price(g, n)
        assert "gold" not in after and after["food"] == before[n].get("food", 0) + before[n]["gold"], n
    assert plain_train.price(g, "MILITIA") == before["MILITIA"]


def test_a_part_of_the_stone_of_castles_and_towers_becomes_wood(monkeypatch):
    monkeypatch.setitem(plain_train.BY_KEY["costs"], "TEST_PART", [[["CASTLE", "WATCH_TOWER"], "stone>wood", 0.4]])
    server, g = setup("SLAVS")
    before = {n: plain_build.price(g, n) for n in ("CASTLE", "WATCH_TOWER", "HOUSE")}
    g.techs.add("TEST_PART")
    for n in ("CASTLE", "WATCH_TOWER"):
        b, after = before[n], plain_build.price(g, n)
        move = int(b["stone"] * 0.4 + 0.5)
        assert after["stone"] == b["stone"] - move and after["wood"] == b.get("wood", 0) + move, n
    assert plain_build.price(g, "HOUSE") == before["HOUSE"]
