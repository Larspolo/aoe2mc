"""The Saxon team bonus of the repair (#1929, AoE2 wiki "Saxons"; "Repairing", Boosts): the repairers of the Saxons
and their allies work faster (civs.REPAIR_TEAM). The Georgian cost bonus is for buildings only."""
import pytest
import test_repair
import test_repair_ship
from test_repair_civs import players

from game import civs, repair, train


def house(*rows):
    """The hit points that one villager of player 1 repairs on a house in two ticks, with the players rows."""
    server, g = test_repair.setup(house=100)
    players(g, *rows)
    k = repair.uuid(test_repair.HOUSE)
    repair.order(g, "Steve", (4, 5))
    before = server.hp[k]
    g.villagers["v0"].state = "repair"
    repair.tick(g, 8.0)
    repair.tick(g, 8.0)
    return server.hp[k] - before


def test_a_saxon_and_an_ally_of_a_saxon_repair_faster():
    plain, k = house((1, "BRITONS", None)), civs.REPAIR_TEAM["SAXONS"]
    assert house((1, "SAXONS", None)) == pytest.approx(plain * k, abs=1) != plain
    assert house((1, "BRITONS", 1), (2, "SAXONS", 1)) == pytest.approx(plain * k, abs=1)
    assert house((1, "BRITONS", 1), (2, "SAXONS", 2)) == plain               # an enemy: no bonus


def test_the_roman_and_the_saxon_factors_multiply_and_two_saxons_do_not_add_up():
    _, g = test_repair.setup()
    players(g, (1, "ROMANS", 1), (2, "SAXONS", 1))
    assert civs.repair_rate(g) == pytest.approx(civs.REPAIR["ROMANS"] * civs.REPAIR_TEAM["SAXONS"])
    players(g, (1, "SAXONS", 1), (2, "SAXONS", 1))
    assert civs.repair_rate(g) == civs.REPAIR_TEAM["SAXONS"]


def test_a_georgian_pays_the_normal_cost_for_the_repair_of_a_ship_and_less_for_a_building():
    server, g = test_repair_ship.setup()
    base = repair.cost(g, "HOUSE")["wood"]
    players(g, (1, "GEORGIANS", None))
    assert repair.unit_order(g, "Steve", "ship")
    steps = 0
    while g.villagers["v0"].state != "idle" and steps < 20000:
        g.step()
        steps += 1
    full, lost = train.price(g, "GALLEY"), test_repair_ship.GALLEY - 60
    assert 100 - g.stock["wood"] == int(full["wood"] / 2 * lost / test_repair_ship.GALLEY)
    assert 100 - g.stock["gold"] == int(full["gold"] / 2 * lost / test_repair_ship.GALLEY)
    assert repair.cost(g, "HOUSE") == {"wood": base * civs.REPAIR_COST["GEORGIANS"]}
