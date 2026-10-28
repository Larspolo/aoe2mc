"""#3283: the mill queues farm reseeds; an empty own farm takes one at once, and its farmer farms on."""
from test_gather_farms import farm_map

from game import gather, savegame, train


def test_seed_farm_costs_60_wood_and_queues_one_reseed():
    assert "FARM_RESEED" in train.AGAIN
    server, g = farm_map()
    g.stock.update(wood=100)
    rect = next(r for r, n in train.homes(g).items() if n == "MILL")
    assert train.queue(g, "Steve", rect[::2], "FARM_RESEED")
    for _ in range(5):
        train.tick(g, 1)
    assert g.stock["wood"] == 100 - train.COSTS["FARM_RESEED"]["wood"] and g.reseeds == 1
    assert any("Reseeds queued: 1" in c for c in server.log)
    server.log.clear()
    assert not train.queue(g, "Steve", rect[::2], "FARM_RESEED")        # 40 wood: not enough, it says why
    assert any("Not enough resources" in c for c in server.log)


def test_an_empty_farm_takes_a_queued_reseed_and_the_farmer_continues():
    server, g = farm_map()
    g.reseeds = 1
    g.select("v")
    g.send((10, 10))
    for _ in range(20000):
        g.step()
        if g.reseeds == 0:
            break
    v = g.villagers["v"]
    assert g.reseeds == 0 and g.map.farms[(10, 10)] > gather.FARM_FOOD - 20
    assert v.tree == (10, 10) and g.farmers.get((10, 10)) == "v" and v.state != "idle"
    assert any(c.startswith("fill 9 63 9 11 64 11 minecraft:farmland replace minecraft:dirt") for c in server.log)


def test_an_empty_farm_without_a_reseed_stops_its_farmer():
    _, g = farm_map()
    g.select("v")
    g.send((10, 10))
    for _ in range(20000):
        g.step()
        if g.villagers["v"].state == "idle":
            break
    assert g.map.farms[(10, 10)] == 0 and g.villagers["v"].tree is None


def test_the_queue_is_saved():
    assert "reseeds" in savegame.OPTIONAL
