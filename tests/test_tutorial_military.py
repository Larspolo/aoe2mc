"""The military steps and the end of the tutorial (#5163): each check with a fake game state, the camp setup and the
end with a title and cheats.over."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import tutorial  # noqa: E402

ROW = {s["name"]: s for s in tutorial.STEPS}


def fake(**kw):
    g = types.SimpleNamespace(**{"stock": {"wood": 0, "food": 0, "gold": 0, "stone": 0}, "queues": {}, "techs": set(),
                                 "data": {"objects": []}, "sites": [], "player": 1, "sent": [], "soldiers": {},
                                 "forts": {}} | kw)
    g.command = lambda c: g.sent.append(c) or ""
    return g


def test_order_after_economy():
    names = [s["name"] for s in tutorial.STEPS]
    assert names[names.index("feudal") + 1:] == ["barracks", "militia", "camp"]


def test_barracks():
    g = fake()
    assert not tutorial.done(g, ROW["barracks"])
    g.sites.append({"name": "BARRACKS", "player": 1, "done": True})
    assert tutorial.done(g, ROW["barracks"])


def test_militia():
    g, need = fake(), ROW["militia"]["count"]
    g.soldiers = {f"u{k}": "MILITIA" for k in range(need - 1)} | {"s": "SCOUT_CAVALRY"}
    assert not tutorial.done(g, ROW["militia"])
    g.soldiers["last"] = "MILITIA"
    assert tutorial.done(g, ROW["militia"])


def target(rect):
    import combat
    x0, x1, z0, z1 = rect
    return combat.target_uuid([x0, z0, x1, z1])


def test_camp_setup_and_destroyed(monkeypatch):
    import build
    rects = iter([(0, 4, 0, 4), (8, 12, 0, 4), (16, 20, 0, 4), (24, 28, 0, 4)])
    found = []
    monkeypatch.setattr(build, "near", lambda g, name, at, reach=0: next(rects))
    monkeypatch.setattr(build, "found", lambda g, name, rect, free=False: found.append((name, g.player)) or
                        {"name": name, "footprint": rect})
    monkeypatch.setattr(build, "rise", lambda g, site, t: g.forts.setdefault(target(site["footprint"]), ()))
    g = fake(map=types.SimpleNamespace(n=64))
    tutorial.show(g, [s["name"] for s in tutorial.STEPS].index("camp"))
    assert len(found) == sum(ROW["camp"]["camp"].values()) and {p for _, p in found} == {2} and g.player == 1
    assert len(g.tutorial_camp) == len(found)
    assert not tutorial.done(g, ROW["camp"])
    g.forts.clear()
    assert tutorial.done(g, ROW["camp"])


def test_end_title_and_over(monkeypatch):
    import cheats
    ended = []
    monkeypatch.setattr(cheats, "over", lambda g, won: ended.append((won(1), won(2))))
    monkeypatch.setattr(tutorial, "done", lambda g, row: True)
    g = fake(tutorial_step=len(tutorial.STEPS) - 1)
    tutorial.tick(g)
    assert any("Tutorial complete" in c and "title" in c for c in g.sent) and ended == [(True, False)]
