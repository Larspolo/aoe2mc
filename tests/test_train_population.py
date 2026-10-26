"""game/train.py: the population limit is 5 per complete own town center and house, at most 200; at the limit the
queue waits, and the sidebar shows the population and the limit (#613)."""
from test_gather import FakeServer, grid

from game import gather, train


def setup(houses=0, food=1000):
    """A flat 24 × 24 map (tile size 1): a town center of player 1 at blocks x 2-4, z 2-4, houses of player 1, a house
    of player 2 and one villager. The FakeServer knows the trained villagers, so the count finds them alive."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "building", "name": "HOUSE", "player": 2, "tile": [20, 20], "footprint": [19, 19, 21, 21]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [7.5, 7.5]}]
    objects += [{"kind": "building", "name": "HOUSE", "player": 1, "tile": [10 + 2 * i, 15],
                 "footprint": [9 + 2 * i, 14, 11 + 2 * i, 16]} for i in range(houses)]
    server = FakeServer({"v": {"Pos": (7.5, 64.0, 7.5)}})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()
    g.stock["food"] = food
    return server, g


def train_all(g, server, seconds):
    """Run the queues for AoE2 seconds; each trained villager also exists on the FakeServer."""
    out = []
    for _ in range(round(seconds / 0.5)):
        for v in train.tick(g, 0.5):
            server.entities[v.uuid] = {"Pos": v.pos}
            out.append(v)
    return out


def test_the_limit_is_5_per_own_town_center_and_house_and_at_most_200():
    server, g = setup(houses=2)
    assert train.limit(g) == 15                                        # the house of player 2 gives nothing
    g.sites.append({"name": "HOUSE", "player": 1, "footprint": [0, 2, 20, 22], "progress": 0.5})
    assert train.limit(g) == 15                                        # a construction site gives nothing
    g.sites[0]["done"] = True
    assert train.limit(g) == 20
    _, g = setup(houses=45)
    assert train.limit(g) == train.LIMIT == 200


def test_the_sidebar_shows_the_population_and_the_limit():
    server, g = setup()
    assert "scoreboard players set Population aoe_res 1" in server.log
    assert "scoreboard players set Limit aoe_res 5" in server.log
    train.queue(g, "Steve", (3, 3))
    train_all(g, server, train.TRAIN_TIMES["VILLAGER_MALE"])
    assert server.log[-1] == "scoreboard players set Population aoe_res 2"
    del server.entities["v"]                                           # the villager dies
    train_all(g, server, train.CENSUS)
    assert server.log.count("scoreboard players set Population aoe_res 1") == 2 and g.pop == 1


def test_the_queue_waits_at_the_limit_until_a_house_is_complete():
    server, g = setup()
    for _ in range(6):
        train.queue(g, "Steve", (3, 3))
    assert len(train_all(g, server, 6 * train.TRAIN_TIMES["VILLAGER_MALE"])) == 4      # 1 + 4 = the limit 5
    assert g.pop == 5 and len(g.queues[2, 5, 2, 5]) == 2 and g.queues[2, 5, 2, 5][0]["progress"] == 0
    said = [c for c in server.log if c.startswith("tellraw Steve") and "limit (5/5)" in c]
    assert len(said) == 1 and "build more houses" in said[0]          # once, not each tick
    g.sites.append({"name": "HOUSE", "player": 1, "footprint": [0, 2, 20, 22], "progress": 1.0, "done": True})
    new = train_all(g, server, 2 * train.TRAIN_TIMES["VILLAGER_MALE"])
    assert len(new) == 2 and g.pop == 7 and "scoreboard players set Limit aoe_res 10" in server.log


def test_two_town_centers_do_not_train_past_the_limit():
    server, g = setup()
    g.data["objects"].append({"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [15.5, 3.5],
                              "footprint": [14, 2, 17, 5]})
    train.census(g)
    for cell in [(3, 3), (15, 3)] * 6:
        train.queue(g, "Steve", cell)
    train_all(g, server, 10 * train.TRAIN_TIMES["VILLAGER_MALE"])
    assert g.pop == train.limit(g) == 10 and len(g.villagers) == 10
