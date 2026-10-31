"""The economy steps of the tutorial (#5162): each check with a fake game state, the setup gives resources."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import tutorial  # noqa: E402

ROW = {s["name"]: s for s in tutorial.STEPS}
TC = (0, 15, 0, 15)


def fake(**kw):
    g = types.SimpleNamespace(**{"stock": {"wood": 0, "food": 0, "gold": 0, "stone": 0}, "queues": {}, "techs": set(),
                                 "data": {"objects": [{"kind": "building", "name": "TOWN_CENTER", "player": 1,
                                                       "footprint": [0, 0, 15, 15]}]},
                                 "sites": [], "player": 1, "sent": []} | kw)
    g.command = lambda c: g.sent.append(c) or ""
    return g


def test_order():
    names = [s["name"] for s in tutorial.STEPS]
    assert names[names.index("house") + 1:names.index("feudal") + 1] == ["villager", "camps", "food", "feudal"]


def test_villager():
    g = fake()
    assert not tutorial.done(g, ROW["villager"])
    g.queues = {(99, 100, 99, 100): [{"name": "VILLAGER", "player": 1}], TC: []}   # not a town center
    assert not tutorial.done(g, ROW["villager"])
    g.queues[TC] = [{"name": "VILLAGER", "player": 1}]
    assert tutorial.done(g, ROW["villager"])


def test_camps():
    g, need = fake(), ROW["camps"]["buildings"]
    g.sites = [{"name": need[0], "player": 1, "done": True}] + [{"name": n, "player": 1, "done": False} for n in need[1:]]
    assert not tutorial.done(g, ROW["camps"])
    for s in g.sites:
        s["done"] = True
    assert tutorial.done(g, ROW["camps"])


def test_food():
    g, need = fake(), ROW["food"]["need"]
    g.stock["food"] = need - 1
    assert not tutorial.done(g, ROW["food"])
    g.stock["food"] = need
    assert tutorial.done(g, ROW["food"])


def test_feudal():
    import build
    g = fake()
    assert not tutorial.done(g, ROW["feudal"])
    g.techs = {build.AGE_TECHS[0]}
    assert tutorial.done(g, ROW["feudal"])


def test_setup_gives():
    g = fake()
    n = [s["name"] for s in tutorial.STEPS].index("villager")
    tutorial.show(g, n)
    assert g.stock == {"wood": 0, "gold": 0, "stone": 0} | ROW["villager"]["give"]
