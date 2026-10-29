"""The Gurjara mills take up to n herdable animals, and the animals inside make a × ln(F / b + 1) food per AoE2 minute
for F food of all of them, with no end (AoE2 DE wiki "Gurjaras", "Mill (Age of Empires II)", #2342). n, a and b come
from the data (civs.HERD_FOOD)."""
import math

import pytest
from test_garrison_game import Server, arrive
from test_gather import grid

from game import civs, combat, garrison, gather

MILL = (10, 12, 2, 4)
TOWER = (16, 18, 2, 4)
N, A, B = civs.HERD_FOOD["GURJARAS"]["MILL"]


def setup(civ, sheep=N + 2):
    """A flat 24 × 24 map: an own mill and watch tower, sheep, one cow and one villager south of them."""
    objects = [{"kind": "building", "name": "MILL", "player": 1, "tile": [11.0, 3.0], "footprint": [10, 2, 12, 4]},
               {"kind": "building", "name": "WATCH_TOWER", "player": 1, "tile": [17.0, 3.0], "footprint": [16, 2, 18, 4]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [6.5, 12.5]},
               {"kind": "unit", "name": "COW_A", "player": 1, "uuid": "cow", "tile": [8.5, 12.5]}]
    objects += [{"kind": "unit", "name": "SHEEP", "player": 1, "uuid": f"s{k}", "tile": [4.5 + k, 9.5]} for k in range(sheep)]
    server = Server({f"s{k}": {"Pos": (4.5 + k, 64.0, 9.5)} for k in range(sheep)} |
                    {"v": {"Pos": (6.5, 64.0, 12.5)}, "cow": {"Pos": (8.5, 64.0, 12.5)},
                     "Steve": {"Pos": (3.5, 64.0, 9.5), "Rotation": (180, 15)}})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()
    g.data["players"] = {"1": {"civ": civ}}
    g.paper = True
    server.targets = {combat.target_uuid(o["footprint"]) for o in objects if o["kind"] == "building"}
    return server, g


def fill(server, g, units):
    g.choose(set(units) | {"v"}, "v")
    assert garrison.order(g, "Steve", (10, 2)) == MILL
    assert "v" not in g.entering                                         # a villager does not go into a mill
    arrive(server, g, MILL)
    g.herd_food = 0.0                                                    # the food of the step in arrive


def test_a_gurjara_mill_takes_n_herdables_and_no_villager():
    server, g = setup("GURJARAS")
    fill(server, g, [f"s{k}" for k in range(N + 2)])
    assert len(g.garrisons[MILL]) == N                                   # the others stay at the door
    assert garrison.inside(g) <= g.flock


@pytest.mark.parametrize("sheep", [1, N])
def test_the_herdables_in_a_mill_make_the_aoe2_food_per_minute(sheep):
    server, g = setup("GURJARAS")
    fill(server, g, [f"s{k}" for k in range(sheep)])
    food = g.stock["food"]
    for _ in range(60):
        garrison.pasture(g, 1.0)
    assert g.stock["food"] - food == int(A * math.log(gather.hunt_food("SHEEP") * sheep / B + 1))


def test_a_cow_counts_its_food():
    server, g = setup("GURJARAS", sheep=0)
    fill(server, g, ["cow"])
    food = g.stock["food"]
    for _ in range(120):
        garrison.pasture(g, 1.0)
    assert g.stock["food"] - food == int(2 * A * math.log(gather.hunt_food("COW_A") / B + 1))


def test_the_mill_of_another_civilization_and_a_tower_take_no_herdable():
    server, g = setup("BRITONS")
    assert MILL not in garrison.holders(g)
    g.choose({"s0", "s1"}, "s0")
    assert garrison.order(g, "Steve", (10, 2)) is None
    server, g = setup("GURJARAS")
    g.choose({"s0", "s1"}, "s0")
    assert garrison.order(g, "Steve", (16, 2)) is None                   # a sheep does not go into a tower
    food = g.stock["food"]
    garrison.pasture(g, 60.0)
    assert g.stock["food"] == food                                       # no animal inside: no food
