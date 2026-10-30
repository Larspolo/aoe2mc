"""The unique technology of the Cumans in the Imperial Age (#4330): the castle of the Cumans researches Cuman
Mercenaries. After it, each castle of the researcher and of its allies trains a count of free units (the key "free"
of data/train.jsonl: Elite Kipchaks), counted per castle; an enemy gets none."""
import types

from test_gather import FakeServer, grid
from test_train_castle import menus, setup

from game import build, gather, train

TECH = "CUMAN_MERCENARIES"
CASTLES = {(12, 4): (10, 14, 2, 6), (20, 16): (18, 22, 14, 18)}
BUILDING, UNIT, COUNT = train.value("free", TECH)


def game(civ="BRITONS", team=1):
    """Player 1 (civ, team) with two castles and a town center in the Imperial Age, and a peer: player 2, Cumans of
    team 1, who researched the technology."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]}]
    objects += [{"kind": "building", "name": BUILDING, "player": 1, "tile": [float(x), float(z)],
                 "footprint": [r[0], r[2], r[1], r[3]]} for (x, z), r in CASTLES.items()]
    players = {"1": {"civ": civ, "color": "blue", "team": team}, "2": {"civ": "CUMANS", "color": "red", "team": 1}}
    server = FakeServer({"Steve": {"Pos": (12.0, 64.0, 9.5), "Rotation": (180, 15)}})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects) | {"players": players}, start={}).setup()
    g.stock.update(food=0, wood=0, gold=0)
    g.techs.update(build.AGE_TECHS[:3])
    g.peers = (types.SimpleNamespace(player=2, techs={TECH}),)
    return g


def test_only_the_castle_of_the_cumans_researches_cuman_mercenaries():
    server, g = setup("CUMANS", ages=3)
    train.open_menu(g, "Steve", (12, 4))
    label = train.layout(g, train.home(g, (12, 4)))[TECH][2]
    assert f":{label}:" in menus(server)[-1]
    _, g = setup("BRITONS", ages=3)
    assert TECH not in train.layout(g, train.home(g, (12, 4)))


def test_the_research_gives_the_researcher_free_units():
    server, g = setup("CUMANS", food=3000, gold=3000, ages=3)
    assert train.queue(g, "Steve", (12, 4), TECH)
    train.tick(g, train.seconds(g, TECH, BUILDING))
    assert TECH in g.techs
    rect = train.home(g, (12, 4))
    assert train.free_left(g, rect, UNIT) == COUNT and train.price(g, UNIT, BUILDING, rect) == {}


def test_an_ally_trains_the_free_units_per_castle():
    g = game()
    a, b = CASTLES.values()
    assert UNIT in train.layout(g, a) and train.price(g, UNIT, BUILDING, a) == {}
    for _ in range(COUNT):
        assert train.queue(g, "Steve", (12, 4), UNIT)
    assert UNIT not in train.layout(g, a) and not train.queue(g, "Steve", (12, 4), UNIT)
    assert train.free_left(g, b, UNIT) == COUNT and UNIT in train.layout(g, b)
    assert all(e.get("free") for e in g.queues[a]) and g.stock == {**g.stock, "food": 0, "wood": 0, "gold": 0}


def test_a_cancel_gives_the_free_unit_back():
    g = game()
    a = CASTLES[12, 4]
    train.queue(g, "Steve", (12, 4), UNIT)
    assert train.free_left(g, a, UNIT) == COUNT - 1
    train.cancel(g, "Steve", a, 0)
    assert train.free_left(g, a, UNIT) == COUNT


def test_an_enemy_gets_no_free_units():
    g = game(team=2)
    a = CASTLES[12, 4]
    assert UNIT not in train.layout(g, a) and not train.queue(g, "Steve", (12, 4), UNIT)
