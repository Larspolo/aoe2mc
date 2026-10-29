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


BASE = next(r["name"] for r in civs.ROWS if r["name"] not in civs.EXTRA)   # a civilization with no second resource


@pytest.mark.parametrize("civ, res, kind", [("POLES", "stone", "stone"), ("PORTUGUESE", "food", "forage"),
                                            ("PURU", "stone", "stone"), ("SHU", "wood", "wood")])
def test_ten_loads_give_the_amount_of_the_second_resource(civ, res, kind):
    second, each = civs.EXTRA[civ][kind]
    g, side = loads(civ, res)
    assert g.stock[res] >= 100
    assert g.stock[second] == side[second] == pytest.approx(each * g.stock[res], abs=1)
    _, base = loads(BASE, res)
    assert base[second] == 0                                           # no bonus: only the gathered resource


def test_the_fractions_add_up_to_the_exact_sum():
    g, _ = loads("SHU", "wood", n=3)
    each = civs.EXTRA["SHU"]["wood"][1]
    assert g.stock["food"] == int(each * g.stock["wood"] + 1e-9)
    assert g.seconds["food"] == pytest.approx(each * g.stock["wood"] - g.stock["food"])


@pytest.mark.parametrize("civ", ["PORTUGUESE", "POLES"])
def test_only_the_named_work_earns_the_second_resource(civ):
    res = next(r for r in ("stone", "wood") if r not in civs.EXTRA[civ])   # a work with no second resource
    _, side = loads(civ, res, n=2)
    assert side[res] >= 20
    assert all(side[second] == 0 for second, _ in civs.EXTRA[civ].values() if second != res)
    assert civs.extra(game("PURU")[1], "no_such_work") is None
