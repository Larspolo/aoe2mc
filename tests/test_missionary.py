"""Missionary (#1939): the monastery of the Spanish trains the missionary in the Castle Age, with the values of the AoE2
DE wiki "Missionary". A mounted monk: it heals, converts in its own range (monk.MONKS) and carries relics as a monk."""
import pytest
from menu_line import item
from test_gather import FakeServer, grid
from test_monk_heal import HealServer
from test_train_castle import menus

import buildings
from game import build, gather, monk, train

MONASTERY = (12, 4)
WITH = min(set(buildings.CIV_TO_ARCH) - set(train.civs.MISSING["MISSIONARY"]))   # the Spanish


def setup(civ, food=30, gold=100):
    """A flat 24 × 24 map (tile size 1): a monastery of player 1 at blocks x 10-13, z 2-5, in the Castle Age."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "building", "name": "MONASTERY", "player": 1, "tile": [12.0, 4.0], "footprint": [10, 2, 14, 6]}]
    data = grid([[64] * 24 for _ in range(24)], objects) | {"players": {"1": {"civ": civ, "color": "blue"}}}
    server = FakeServer({"Steve": {"Pos": (12.0, 64.0, 9.5), "Rotation": (180, 15)}})
    g = gather.Gather(server, data, start={}).setup()
    g.stock.update(food=food, gold=gold)
    g.techs.update(build.AGE_TECHS[:2])
    return server, g


def test_the_monastery_of_the_spanish_trains_the_missionary():
    server, g = setup(WITH, food=1000, gold=1000)
    rect = train.open_menu(g, "Steve", MONASTERY)
    slot = train.SLOTS["MISSIONARY"]
    assert item(menus(server)[-1], "Missionary").startswith(f"{slot}:")
    assert train.order(g, "Steve", rect, slot) == 1 and g.queues[rect][0]["name"] == "MISSIONARY"
    uuid, = train.tick(g, train.seconds(g, "MISSIONARY", "MONASTERY"))
    assert g.soldiers[uuid] == "MISSIONARY" and uuid not in g.villagers   # it does not gather
    server, g = setup(min(train.civs.MISSING["MISSIONARY"]))
    train.open_menu(g, "Steve", MONASTERY)
    assert "Missionary" not in menus(server)[-1]


def units_map(server_class, others, ents):
    objects = [{"kind": "unit", "name": "MISSIONARY", "player": 1, "uuid": "m", "tile": [5.5, 5.5]}]
    for uuid, name, player, x in others:
        objects.append({"kind": "unit", "name": name, "player": player, "uuid": uuid, "tile": [x, 5.5]})
    server = server_class(ents)
    return server, gather.Gather(server, grid([[64] * 40 for _ in range(40)], objects)).setup()


def test_the_missionary_heals():
    ents = {"m": {"Pos": (5.5, 64.0, 5.5), "Health": 30.0, "Max": 30.0}, "a": {"Pos": (8.5, 64.0, 5.5), "Health": 10.0, "Max": 40.0}}
    server, g = units_map(HealServer, [("a", "MILITIA", 1, 8.5)], ents)
    assert g.soldiers["m"] == "MISSIONARY"
    for _ in range(5):
        monk.heal(g, monk.EVERY)
    assert server.entities["a"]["Health"] == pytest.approx(10 + 4 * monk.RATE)


def test_the_missionary_converts_in_its_own_range():
    x = 5.5 + monk.MONKS["MISSIONARY"] + 1                            # 1 tile out of its range
    ents = {"m": {"Pos": (5.5, 64.0, 5.5)}, "foe": {"Pos": (x, 64.0, 5.5)}}
    server, g = units_map(FakeServer, [("foe", "MILITIA", 2, x)], ents)
    assert monk.convert_order(g, {"m"}, "foe")
    monk.convert(g, 1.0)
    assert "foe" in g.enemies and any(c.startswith("aoe moveto m ") for c in server.log)   # out of range: it walks
    server.entities["m"]["Pos"] = (7.0, 64.0, 5.5)                    # 1.5 tiles nearer: in range, it converts
    for _ in range(80):
        monk.convert(g, 0.25)
    assert "foe" not in g.enemies and "foe" in g.soldiers


def test_a_monk_converts_a_missionary_only_with_atonement():
    ents = {"m": {"Pos": (5.5, 64.0, 5.5)}, "e": {"Pos": (8.5, 64.0, 5.5)}}
    server, g = units_map(FakeServer, [("e", "MISSIONARY", 2, 8.5)], ents)
    assert not monk.convertible(g, "e")
    g.techs.add("ATONEMENT")
    assert monk.convertible(g, "e")


def test_the_missionary_carries_a_relic_into_the_monastery():
    objects = [{"kind": "unit", "name": "MISSIONARY", "player": 1, "uuid": "m", "tile": [5.5, 5.5]},
               {"kind": "other", "name": "RELIC", "player": 0, "tile": [10.5, 5.5]},
               {"kind": "building", "name": "MONASTERY", "player": 1, "footprint": [14, 2, 18, 6]}]
    server = HealServer({"m": {"Pos": (5.5, 64.0, 5.5), "Health": 30.0, "Max": 30.0}})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()
    g.paper = True
    g.choose({"m"}, "m")
    assert monk.order(g, "Steve", (10, 6)) and g.fetching == {"m": ("relic", 0)}
    server.entities["m"]["Pos"] = (10.5, 64.0, 6.5)
    monk.relic_tick(g, monk.EVERY)
    assert monk.carriers(g) == {"m": 0}
    assert monk.order(g, "Steve", (15, 3))
    x, z = next(iter(g.map.front((14, 18, 2, 6))))
    server.entities["m"]["Pos"] = (x + 0.5, 64.0, z + 0.5)
    monk.relic_tick(g, monk.EVERY)
    assert g.relics[0]["home"] == (14, 18, 2, 6) and not monk.carriers(g)
