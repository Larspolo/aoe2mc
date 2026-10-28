"""game/gather.py: the gatherers of some civilizations earn a second resource (civs.EXTRA, AoE2 DE wiki, #2113)."""
import pytest
from test_gather import FakeServer, grid

from game import civs, gather

TARGETS = {"stone": (12, 18), "food": (10, 10), "wood": (16, 6)}


def game(civ):
    """A flat 24 × 24 map (tile size 1): a town center and a villager of player 1 (civilization civ), a stone mine, a
    fruit bush and two trees."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "footprint": [2, 2, 5, 5]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [7.5, 7.5]},
               {"kind": "other", "name": "STONE_MINE", "tile": [12.5, 18.5]},
               {"kind": "other", "name": "FRUIT_BUSH", "tile": [10.5, 10.5]},
               {"kind": "other", "name": "TREE_OAK", "tile": [16.5, 6.5]},
               {"kind": "other", "name": "TREE_OAK", "tile": [17.5, 6.5]}]
    data = grid([[64] * 24 for _ in range(24)], objects)
    data["players"] = {"1": {"civ": civ, "color": 0}}
    server = FakeServer({"v": {"Pos": (7.5, 64.0, 7.5)}})
    return server, gather.Gather(server, data, carry=10, chop=0.25, start={}).setup()


def loads(civ, res, n=10):
    """The stock and the sidebar income after n loads of res (10 each) at the town center."""
    server, g = game(civ)
    g.select("v")
    g.send(TARGETS[res])
    for _ in range(40000):
        g.step()
        if g.stock[res] >= 10 * n:
            break
    side = {r: sum(int(c.split()[-1]) for c in server.log if c.startswith(f"scoreboard players add {r.capitalize()} aoe_res"))
            for r in ("wood", "food", "gold", "stone")}
    return g, side


@pytest.mark.parametrize("civ, res, second, amount", [
    ("POLES", "stone", "gold", 33),                                    # stone miners: gold 33 % of the stone
    ("PORTUGUESE", "food", "wood", 33),                                # foragers: wood 0.33 for each food
    ("PURU", "stone", "food", 69),                                     # stone miners: food 0.69 for each stone
    ("SHU", "wood", "food", 7),                                        # lumberjacks: food 0.7 for each 10 wood
])
def test_ten_loads_give_the_aoe2_amount_of_the_second_resource(civ, res, second, amount):
    g, side = loads(civ, res)
    assert g.stock[res] >= 100
    assert g.stock[second] == side[second] == pytest.approx(amount * g.stock[res] / 100, abs=1)
    _, base = loads("GOTHS", res)
    assert base[second] == 0                                           # no bonus: only the gathered resource


def test_the_fractions_add_up_to_the_exact_sum():
    g, _ = loads("SHU", "wood", n=3)
    assert g.stock["food"] == int(0.07 * g.stock["wood"] + 1e-9)
    assert g.seconds["food"] == pytest.approx(0.07 * g.stock["wood"] - g.stock["food"])


def test_only_the_named_work_earns_the_second_resource():
    _, side = loads("PORTUGUESE", "stone", n=2)                        # a Portuguese miner: no wood
    assert side["wood"] == 0 and side["stone"] >= 20
    _, side = loads("POLES", "wood", n=2)                              # a Polish lumberjack: no gold
    assert side["gold"] == 0
    assert civs.extra(game("PURU")[1], "gold") is None
