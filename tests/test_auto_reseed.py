"""#3422: the AoE2 DE toggle "Auto reseed" of the mill: with it on, a farmer rebuilds its empty farm at once with the
wood of the farm cost; a queued reseed (#3283) goes first."""
import json
from urllib.parse import unquote

from test_gather_farms import farm_map

from game import build, gather, savegame, train


def farm(g, done):
    """The farmer works the farm at 10 10 until done(g) or it stands idle."""
    g.select("v")
    g.send((10, 10))
    for _ in range(20000):
        g.step()
        if done(g) or g.villagers["v"].state == "idle":
            break
    return g.villagers["v"]


def wood():
    return build.price(None, "FARM")["wood"]


def test_the_mill_menu_shows_the_switch_and_a_click_switches_it():
    server, g = farm_map()
    rect = next(r for r, n in train.homes(g).items() if n == "MILL")
    slot = train.ITEMS["AUTO_RESEED"][0]
    assert "AUTO_RESEED" in train.layout(g, rect)
    stock = dict(g.stock)
    train.show(g, "Steve", rect)
    assert any("Auto reseed:free · 0 s · off" in unquote(c) for c in server.log)
    server.log.clear()
    assert train.order(g, "Steve", rect, slot) == 1
    assert g.auto_reseed is True and g.stock == stock and not g.queues.get(rect)   # no cost and no queue
    assert any("Auto reseed: on." in c for c in server.log)
    assert any("Auto reseed:free · 0 s · on" in unquote(c) for c in server.log)
    train.order(g, "Steve", rect, slot)
    assert g.auto_reseed is False


def test_with_the_switch_on_the_farmer_pays_the_farm_and_farms_on():
    server, g = farm_map()
    g.auto_reseed, g.stock["wood"] = True, 100
    v = farm(g, lambda g: g.stock["wood"] < 100)
    assert g.stock["wood"] == 100 - wood() and g.map.farms[(10, 10)] > gather.FARM_FOOD - 20
    assert v.tree == (10, 10) and v.state != "idle"


def test_with_too_little_wood_or_the_switch_off_the_farmer_stops():
    for on, w in ((True, wood() - 1), (False, 100)):
        _, g = farm_map()
        g.auto_reseed, g.stock["wood"] = on, w
        v = farm(g, lambda g: False)
        assert (10, 10) not in g.map.farms and v.tree != (10, 10) and g.stock["wood"] == w   # the farm is gone (#3423)


def test_a_queued_reseed_goes_before_the_wood():
    _, g = farm_map()
    g.auto_reseed, g.reseeds, g.stock["wood"] = True, 1, 100
    farm(g, lambda g: g.reseeds == 0)
    assert g.reseeds == 0 and g.stock["wood"] == 100


def test_a_save_and_a_load_keep_the_switch():
    server, g = farm_map()
    g.auto_reseed = True
    _, h = farm_map()
    savegame.load(h, json.loads(json.dumps(savegame.dump(g))))
    assert h.auto_reseed is True
