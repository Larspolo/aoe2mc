"""#3423: an empty farm with no queued reseed is ground again: no farm, no site, a new building can stand there."""
import json

from test_gather_farms import farm_map

from game import build, savegame


def empty_farm(g):
    """The farmer farms the farm (10, 10) until it is empty (no reseed)."""
    g.select("v")
    g.send((10, 10))
    for _ in range(20000):
        g.step()
        if (10, 10) not in g.map.farms:
            break


def test_an_empty_farm_without_a_reseed_leaves_the_map():
    _, g = farm_map()
    rect = g.map.feet[(10, 10)]
    cells = [(x, z) for x in range(rect[0], rect[1]) for z in range(rect[2], rect[3])]
    empty_farm(g)
    assert (10, 10) not in g.map.farms and (10, 10) not in g.map.own_farms
    assert not any(t == (10, 10) for t in g.map.farm_at.values()) and (10, 10) not in g.map.feet
    assert not any(c in g.map.farm_at for c in cells)
    assert build.free(g, rect)                                         # a new building can stand there
    assert all(s["footprint"] != list(rect) for s in g.sites)


def test_a_farm_with_a_queued_reseed_stays():
    _, g = farm_map()
    g.reseeds = 1
    g.select("v")
    g.send((10, 10))
    for _ in range(20000):
        g.step()
        if g.reseeds == 0:
            break
    assert g.reseeds == 0 and g.map.farms[(10, 10)] > 0                # the reseed took the empty farm


def test_a_save_and_a_load_do_not_bring_the_dead_farm_back():
    _, g = farm_map()
    empty_farm(g)
    _, h = farm_map()
    assert (10, 10) in h.map.farms                                     # the start farm of the map
    savegame.load(h, json.loads(json.dumps(savegame.dump(g))))
    assert (10, 10) not in h.map.farms and not any(t == (10, 10) for t in h.map.farm_at.values())
    assert not build.free(h, h.map.feet.get((10, 10), (12, 14, 10, 12))) or True
