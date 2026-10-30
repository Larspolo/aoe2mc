"""#2429: a Georgian player starts with a Mule Cart, and Mule Carts replace the Lumber Camps and Mining Camps (AoE2 DE
wiki "Georgians", MediaWiki API: "Start with a Mule Cart. Mule Carts replace Lumber Camps and Mining Camps."). Fake
server of test_gather, the town map of test_empire_wars."""
import pytest
from test_empire_wars import town_map

from game import start_buildings


def georgian(civ="GEORGIANS"):
    g = town_map()
    g.data["players"]["1"]["civ"] = civ
    return g


def test_a_georgian_starts_with_a_complete_mule_cart_for_free():
    g = georgian()
    stock = dict(g.stock)
    site, = start_buildings.place(g)
    assert site["name"] == "MULE_CART" and site.get("done") and g.stock == stock
    x0, x1, z0, z1 = site["footprint"]
    assert abs((x0 + x1) / 2 - 24) + abs((z0 + z1) / 2 - 24) < 10       # next to the town center
    cells = {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
    assert {r for r, sites in g.map.drops.items() if cells in sites} == {"wood", "gold", "stone", "meat"}


def test_a_georgian_villager_drops_wood_and_gold_at_the_mule_cart():
    g = georgian()
    site, = start_buildings.place(g)
    x0, x1, z0, z1 = site["footprint"]
    cells = {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
    tc = {(x, z) for x in range(22, 26) for z in range(22, 26)}
    assert g.map.drops["wood"] == g.map.drops["gold"] == [tc, cells]   # the town center and the cart: no camp
    for res in ("wood", "gold"):
        before = g.stock[res]
        g.send(next(t for t, k in (g.map.trees if res == "wood" else g.map.mines["gold"]).items() if k), {"p1"})
        for _ in range(3000):
            g.step()
            if g.stock[res] > before:
                break
        assert g.stock[res] > before


@pytest.mark.parametrize("civ", ["FRANKS", "ARMENIANS", None])
def test_the_other_civilizations_start_with_no_building(civ):
    g = georgian(civ)
    assert start_buildings.place(g) == [] and not g.sites


def test_only_a_civilization_with_start_buildings_needs_them():
    assert start_buildings.used({"players": {"1": {"civ": "FRANKS"}, "2": {"civ": "GEORGIANS"}}})
    assert not start_buildings.used({"players": {"1": {"civ": "FRANKS"}, "2": {}}})
    assert not start_buildings.used({"players": []})


@pytest.mark.parametrize("state, places", [(None, 1), ({"players": {}}, 0)])
def test_play_places_the_start_buildings_of_a_new_game_only(state, places, tmp_path, monkeypatch):
    import combat
    import gather
    import run
    import savegame
    import start_buildings as plain  # the module object that run.py imports
    from test_play_speed import FakeGame
    (tmp_path / "aoe2mc.json").write_text('{"players": {"1": {"civ": "GEORGIANS"}}, "tile_size": 4}')
    seen = []

    class FakeGather:
        bots, villagers, units, ended, speed = (), [], [], None, 1.0

        def __init__(self, *a, **k):
            pass

        def setup(self):
            pass

        def run(self, seconds):
            pass
    monkeypatch.setattr(gather, "Gather", FakeGather)
    monkeypatch.setattr(plain, "place", seen.append)
    monkeypatch.setattr(combat, "setup", lambda game, data: None)
    monkeypatch.setattr(savegame, "load", lambda g, d: None, raising=False)
    run.play(FakeGame(), str(tmp_path), state=state)
    assert len(seen) == places
