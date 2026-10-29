"""The food drop-off bonuses (#2111): the key "drop" of a civilization (civs.DROP) gives more food for each load at the
drop site ("food"), or for a load of a fruit bush only ("forage"). The fractions go to the next load, as in AoE2. The
tests use their own factors, not the values of game/data/civs.jsonl."""
import pytest
from test_drop_sites import Server, building, data
from test_ship_gather import fish_map

from game import civs, fleet, gather


@pytest.fixture(autouse=True)
def factors(monkeypatch):
    monkeypatch.setattr(civs, "DROP", {"DANES": {"food": 1.05}, "SPARTANS": {"food": 1.1}, "MAPUCHE": {"forage": 1.25}})
    monkeypatch.setattr(civs, "DROP_EXTRA", {})


def game(civ):
    d = data(building("TOWN_CENTER", 30, 30))
    d["players"] = {"1": {"civ": civ}}
    return gather.Gather(Server(), d, start={})


def test_a_food_load_gets_the_bonus_of_the_civilization():
    for civ, two in (("DANES", 21), ("SPARTANS", 22), ("BRITONS", 20), (None, 20)):
        g = game(civ)
        g.deliver("food", 10)
        g.deliver("food", 10)
        assert g.stock["food"] == two, civ
    g = game("DANES")
    g.deliver("food", 10)
    assert g.stock["food"] == 10 and g.spare["food"] == 0.5               # half a food waits for the next load


def test_mapuche_get_more_food_only_from_a_fruit_bush():
    g = game("MAPUCHE")
    g.deliver("food", 10, forage=True)
    g.deliver("food", 10, forage=True)
    assert g.stock["food"] == 25
    g = game("MAPUCHE")
    g.deliver("food", 10)                                              # a farm load
    assert g.stock["food"] == 10
    g = game("DANES")
    g.deliver("food", 10, forage=True)
    assert g.stock["food"] == 10                                       # the Danish bonus is not on top of a forage one


def test_other_resources_get_no_bonus():
    for civ in ("DANES", "SPARTANS", "MAPUCHE"):
        g = game(civ)
        g.deliver("wood", 10)
        g.deliver("gold", 10)
        assert g.stock["wood"] == 10 and g.stock["gold"] == 10, civ


def test_a_forager_at_the_drop_site_earns_the_mapuche_bonus():
    for civ, food in (("MAPUCHE", 12), ("BRITONS", 10)):
        g = game(civ)
        g.map.bushes[(5, 5)] = 100
        v = g.villagers["v"] = gather.Villager("v", (31.5, 64.0, 34.5))
        v.state, v.res, v.load, v.tree, v.path = "to_drop", "food", 10, (5, 5), []
        g.step()
        assert g.stock["food"] == food and v.load == 0, civ


def test_a_danish_fishing_ship_drops_off_more_food():
    server, g, uuid = fish_map()
    g.data["players"]["1"]["civ"] = "DANES"
    v, food = g.ships[uuid], g.stock["food"]
    fleet.fish(g, {uuid}, (20, 12))
    for _ in range(800):
        fleet.tick(g, 0.25)
        if v.state == "to_drop" and not v.path:
            break
    load = v.load
    fleet.tick(g, 0.25)
    assert load and g.stock["food"] + g.spare["food"] == pytest.approx(food + load * 1.05)
