"""The tutorial (#5161): the check of each step with a fake game state, the order of the steps from the data, tick()."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import table  # noqa: E402
import tutorial  # noqa: E402

ROW = {s["name"]: s for s in tutorial.STEPS}


def fake(**kw):
    g = types.SimpleNamespace(**{"selected": set(), "villagers": {}, "stock": {"wood": 0, "food": 0, "gold": 0, "stone": 0},
                                 "data": {"objects": []}, "sites": [], "player": 1, "sent": []} | kw)
    g.command = lambda c: g.sent.append(c) or ""
    return g


def test_order_from_data():
    assert [s["name"] for s in tutorial.STEPS] == [r["name"] for r in table.load("tutorial.jsonl")]


def test_select():
    g = fake(villagers={"v1": object()})
    assert not tutorial.done(g, ROW["select"])
    g.selected = {"s1"}                                       # a soldier is no villager
    assert not tutorial.done(g, ROW["select"])
    g.selected = {"v1"}
    assert tutorial.done(g, ROW["select"])


def test_wood():
    g, need = fake(), ROW["wood"]["need"]
    g.stock["wood"] = need - 1
    assert not tutorial.done(g, ROW["wood"])
    g.stock["wood"] = need
    assert tutorial.done(g, ROW["wood"])


def test_house():
    g = fake()
    g.sites = [{"name": "HOUSE", "player": 1, "done": False}, {"name": "HOUSE", "player": 2, "done": True}]
    assert not tutorial.done(g, ROW["house"])
    g.sites.append({"name": "HOUSE", "player": 1, "done": True})
    assert tutorial.done(g, ROW["house"])


def test_tick_steps(monkeypatch):
    steps = [{"name": "a", "text": "A", "check": "x.a"}, {"name": "b", "text": "B", "check": "x.b"}]
    monkeypatch.setattr(tutorial, "STEPS", steps)
    ready = set()
    monkeypatch.setattr(tutorial, "done", lambda g, row: row["name"] in ready)
    import cheats
    monkeypatch.setattr(cheats, "over", lambda g, won: None)
    g = fake()
    tutorial.tick(g)
    assert g.tutorial_step == 0 and any('"A"' in c for c in g.sent)
    tutorial.tick(g)
    assert g.tutorial_step == 0
    ready.add("a")
    g.sent.clear()
    tutorial.tick(g)
    assert g.tutorial_step == 1 and any("B" in c for c in g.sent) and any("playsound" in c for c in g.sent)
    ready.add("b")
    g.sent.clear()
    tutorial.tick(g)
    assert g.tutorial_step == 2 and any("tutorial is complete" in c for c in g.sent)
    g.sent.clear()
    tutorial.tick(g)
    assert g.sent == []
