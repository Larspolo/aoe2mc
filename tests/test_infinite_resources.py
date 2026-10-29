"""#2489: the AoE2 DE starting resources "Infinite" and "Random" (wiki "Random map", section "Settings"):
`run.py --resources infinite` (a cost does not lower the stock) and `--resources random` (one of the levels)."""
from test_gather import FakeServer, grid

from game import gather, market, train

TC = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]}]


def game(resources, objects=TC, size=24):
    server = FakeServer({})
    return server, gather.Gather(server, grid([[64] * size for _ in range(size)], objects), resources=resources).setup()


def test_a_cost_does_not_lower_the_infinite_resources():
    server, g = game("infinite")
    start = dict(g.stock)
    assert start == gather.LEVELS["infinite"]                          # the start amounts of the level
    assert train.queue(g, "Steve", (3, 3)) == (2, 5, 2, 5)            # a villager
    market.add(g, "gold", -100)                                        # a market buy or a tribute
    assert g.stock == start and g.queues[2, 5, 2, 5]
    assert not any(c.startswith("scoreboard players remove") for c in server.log)   # the sidebar stays
    g.earn("wood", 10)                                                 # an income still counts
    assert g.stock["wood"] == start["wood"] + 10 and "scoreboard players add Wood aoe_res 10" in server.log


def test_the_other_levels_pay_as_before():
    server, g = game("ultra")
    train.queue(g, "Steve", (3, 3))
    food = train.price(g, "VILLAGER_MALE")["food"]
    assert g.stock["food"] == gather.LEVELS["ultra"]["food"] - food
    assert f"scoreboard players remove Food aoe_res {food}" in server.log
    assert type(g.stock) is dict


def test_random_is_one_level_for_each_player_and_each_run():
    data = grid([[64] * 24 for _ in range(24)], TC)
    picked = gather.level("random", data)
    assert picked in {"low", "medium", "high", "ultra"} and picked == gather.level("random", data)
    stocks = [gather.Gather(FakeServer({}), data, player=p, resources="random").stock for p in (1, 2)]
    assert stocks[0] == stocks[1] == gather.LEVELS[picked]
    assert gather.level("high", data) == "high"


def test_random_differs_between_maps():
    picks = {gather.level("random", grid([[64] * n for _ in range(n)], TC) | {"map_size": n}) for n in range(8, 40)}
    assert len(picks) > 1
