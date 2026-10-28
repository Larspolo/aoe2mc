"""game/fleet.py: a fishing ship drops its load when it changes the resource (AoE2 drops a load of another resource).
Fake server, no Minecraft."""
from test_ship_gather import fish_map

from game import fleet


def test_a_ship_drops_its_food_when_it_goes_to_an_oyster():
    server, g, uuid = fish_map()
    v, gold = g.ships[uuid], g.stock["gold"]
    g.map.oysters.add((21, 14))
    v.load, v.res = 10, "food"
    fleet.fish(g, {uuid}, (21, 14))
    assert v.load == 0 and v.res == "gold"
    assert g.stock["gold"] == gold


def test_a_ship_drops_its_gold_when_it_goes_to_a_fish():
    server, g, uuid = fish_map()
    v = g.ships[uuid]
    g.map.oysters.add((21, 14))
    v.load, v.res = 10, "gold"
    fleet.fish(g, {uuid}, (20, 12))
    assert v.load == 0 and v.res == "food"


def test_a_ship_keeps_its_food_when_it_goes_to_another_fish():
    server, g, uuid = fish_map()
    v = g.ships[uuid]
    v.load, v.res = 10, "food"
    fleet.fish(g, {uuid}, (21, 14))
    assert v.load == 10 and v.res == "food"
