"""game/hints.py and game/gather.py: the pending Attack Move, Follow and Guard orders show their hint in the action bar
(as Patrol, #3355), and a Follow or Guard order shows the order marker on its target (#796, #3358)."""
from game import gather, hints, stance

from test_follow_guard_order import setup


def test_each_pending_order_has_its_own_hint(monkeypatch):
    server, g, _ = setup(monkeypatch, stance.FOLLOW)
    for order in ("attack_move", "follow", "guard", "patrol"):
        g.ordering = {"Steve": order}
        assert hints.state(g, "Steve") == (order, hints.TEXTS[order])


def test_a_follow_of_a_unit_sends_the_order_marker_on_the_target(monkeypatch):
    server, g, _ = setup(monkeypatch, stance.FOLLOW)
    monkeypatch.setattr(g, "target", lambda eye, d, places: ("unit", "v-1", {(30, 30)}))
    g.click("Steve")
    assert "effect give v-1 minecraft:glowing 1 0 true" in server.log


def test_a_guard_of_a_building_sends_the_marker_around_its_rect(monkeypatch):
    server, g, _ = setup(monkeypatch, stance.GUARD)
    cells = {(32, 40), (39, 47)}
    monkeypatch.setattr(g, "target", lambda eye, d, places: ("building", (32, 40, 40, 48), cells))
    g.click("Steve")
    assert g.follows == {"m-1": [(32, 40, 40, 48), "guard"]}
    assert server.log[-len(gather.marker(g.map, cells, "go", "Steve")):] == gather.marker(g.map, cells, "go", "Steve")
    assert not any("glowing" in c for c in server.log)

