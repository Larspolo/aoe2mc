"""The civilization bonuses of the repair (#1730, AoE2 wiki "Repairing"): Roman repairers work faster (civs.REPAIR), and
the Georgian team bonus makes the repairs of the buildings of the Georgians and their allies cheaper (civs.REPAIR_COST)."""
import pytest
import test_repair
import test_repair_ship
import test_repair_siege

from game import civs, repair, train


def players(g, *rows):
    """Set the players of g: (number, civilization, team) rows."""
    g.data["players"] = {str(n): {"civ": c} | ({"team": t} if t else {}) for n, c, t in rows}


def tick(setup, key, civ):
    server, g = setup()
    players(g, (1, civ, None))
    store = server.hp if key == "house" else server.health
    k = repair.uuid(test_repair.HOUSE) if key == "house" else key
    if key == "house":
        repair.order(g, "Steve", (4, 5))
    else:
        repair.unit_order(g, "Steve", key)
    before = store[k]
    g.villagers["v0"].state = "repair"
    repair.tick(g, 8.0)
    repair.tick(g, 8.0)
    return store[k] - before


@pytest.mark.parametrize("setup, key", [(lambda: test_repair.setup(house=100), "house"),
                                        (lambda: test_repair_siege.setup(hp=50.0), "ram"),
                                        (lambda: test_repair_ship.setup(hp=30.0), "ship")])
def test_roman_repairers_work_faster(setup, key):
    plain, roman = tick(setup, key, "BRITONS"), tick(setup, key, "ROMANS")
    assert roman == pytest.approx(plain * civs.REPAIR["ROMANS"], abs=1) and civs.REPAIR["ROMANS"] > 1                 # whole hit points of a building


def test_the_georgian_team_bonus_makes_the_repair_cheaper():
    _, g = test_repair.setup()
    base, tc = repair.cost(g, "HOUSE"), repair.cost(g, "TOWN_CENTER")
    k = civs.REPAIR_COST["GEORGIANS"]
    players(g, (1, "GEORGIANS", None), (2, "BRITONS", None))
    assert repair.cost(g, "HOUSE") == {"wood": base["wood"] * k} and repair.cost(g, "TOWN_CENTER") == {"wood": tc["wood"] * k}
    players(g, (1, "BRITONS", 1), (2, "GEORGIANS", 1))                  # an ally of the Georgians
    assert repair.cost(g, "HOUSE") == {"wood": base["wood"] * k}
    players(g, (1, "BRITONS", 1), (2, "GEORGIANS", 2))                  # an enemy: no bonus
    assert repair.cost(g, "HOUSE") == base
    players(g, (1, "GEORGIANS", 1), (2, "GEORGIANS", 1))                # the bonuses do not add up
    assert civs.repair_cost(g) == k


def test_a_georgian_pays_the_normal_cost_for_the_repair_of_a_ram():
    # AoE2 wiki "Villager (Age of Empires II)": "The bonus does not apply to repairing units" (#1929)
    server, g = test_repair_siege.setup(hp=test_repair_siege.RAM - 35)
    players(g, (1, "GEORGIANS", None))
    repair.unit_order(g, "Steve", "ram")
    steps = 0
    while g.villagers["v0"].state != "idle" and steps < 5000:
        g.step()
        steps += 1
    full = train.price(g, "BATTERING_RAM")
    share = 35 / test_repair_siege.RAM
    assert 100 - g.stock["wood"] == int(full["wood"] / 2 * share)
    assert 100 - g.stock["gold"] == int(full["gold"] / 2 * share)


def test_the_docstring_lists_no_roman_repairers_as_missing():
    assert "repairers" not in civs.__doc__.split("REPAIR and")[0]
