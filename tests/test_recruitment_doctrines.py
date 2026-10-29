"""The Recruitment Doctrines of the Macedonians (#2483, epic #1088; AoE2 wiki "Macedonians (Chronicles)"): a free
switch at the barracks, archery range and stable, for each building type: Balanced (no change), Conscript (-15 % food
and wood, +50 % train time) and Mercenary (+10 % food and wood, -50 % train time). A queued unit keeps the cost and
time of its doctrine. Fake server of test_gather."""
import pytest
from menu_line import item
from test_forging import menus
from test_gather import FakeServer, grid

from game import gather, train

HOMES = {"BARRACKS": ([2, 2, 5, 5], "MILITIA"), "ARCHERY_RANGE": ([8, 2, 11, 5], "ARCHER"),
         "STABLE": ([14, 2, 17, 5], "SCOUT_CAVALRY")}


def game(civ="MACEDONIANS"):
    objects = [{"kind": "building", "name": b, "player": 1, "footprint": f} for b, (f, _) in HOMES.items()]
    data = grid([[64] * 24 for _ in range(24)], objects)
    data["players"] = {"1": {"civ": civ, "color": "blue", "arch": "western"}}
    server = FakeServer({"Steve": {"Pos": (11.5, 64.0, 9.5), "Rotation": (180, 15)}})
    g = gather.Gather(server, data, start={}).setup()
    g.stock.update(food=1000, wood=1000, gold=1000)
    return server, g


def rect(building):
    x0, z0, x1, z1 = HOMES[building][0]
    return x0, x1, z0, z1


def cell(building):
    return HOMES[building][0][0], HOMES[building][0][1]


def values(g, building):
    """The cost and the train time of the unit of building with the present doctrine."""
    unit = HOMES[building][1]
    return train.price(g, unit, building), train.seconds(g, unit, building)


@pytest.mark.parametrize("building", sorted(HOMES))
def test_a_macedonian_switches_the_doctrine_of_each_building_type(building):
    server, g = game()
    train.show(g, "Steve", rect(building))
    assert item(" ".join(menus(server)), "Recruitment Doctrine").endswith(":free · 0 s · research")
    unit = HOMES[building][1]
    cost, time = values(g, building)
    name = f"{building}_RECRUITMENT_DOCTRINE"
    stock = dict(g.stock)
    assert train.queue(g, 1, cell(building), name) and g.stock == stock and not g.queues.get(rect(building))   # free, at once
    for k in (1, 2):                                                   # Conscript, then Mercenary: the factors of the data
        _, f, t = train.doctrine(g, building, k)
        assert values(g, building) == ({r: int(v * (f if r in ("food", "wood") else 1) + 0.5) for r, v in cost.items()},
                                       pytest.approx(time * t))
        train.queue(g, 1, cell(building), name)
    assert values(g, building) == (cost, time)                         # Balanced again
    others = [b for b in HOMES if b != building]
    assert all(values(g, b) == values(game()[1], b) for b in others)   # each building type has its own
    assert unit in train.trains(g, building)


def test_a_queued_unit_keeps_the_time_of_its_doctrine():
    server, g = game()
    train.queue(g, 1, cell("BARRACKS"), "BARRACKS_RECRUITMENT_DOCTRINE")   # Conscript
    cost, time = values(g, "BARRACKS")
    assert train.queue(g, 1, cell("BARRACKS"), "MILITIA")
    paid = g.queues[rect("BARRACKS")][0]
    assert paid["doctrine"] == 1 and paid["paid"] == cost
    train.queue(g, 1, cell("BARRACKS"), "BARRACKS_RECRUITMENT_DOCTRINE")   # Mercenary: not for the queued one
    assert values(g, "BARRACKS")[1] < time
    train.tick(g, time - 1)
    assert g.queues[rect("BARRACKS")][0]["progress"] < 1               # the time of Conscript, not of Mercenary


def test_another_civilization_has_no_doctrine():
    server, g = game("BRITONS")
    for building in HOMES:
        train.show(g, "Steve", rect(building))
        assert not train.queue(g, 1, cell(building), f"{building}_RECRUITMENT_DOCTRINE")
    assert menus(server) and item(" ".join(menus(server)), "Recruitment Doctrine") is None
