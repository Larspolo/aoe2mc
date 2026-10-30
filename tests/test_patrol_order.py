"""game/stance.py: the stance menu has a "Patrol" item (slot 6). A click on it and then on a ground cell sends the
selected military units on a patrol between their place and the cell (AoE2 Patrol, #3355); scenario.patrol walks the
legs in each game, and a new order ends the patrol."""
from test_gather import FakeServer, grid

from game import gather, scenario, stance


def setup(monkeypatch):
    """A militia and a villager (player 1), both selected; Patrol chosen in the menu; the next click hits cell (20, 10)."""
    feet = {"m-1": (5.5, 64.0, 10.5), "v-1": (12.5, 64.0, 4.5)}
    names = {"m-1": "MILITIA", "v-1": "VILLAGER_MALE"}
    objects = [{"kind": "unit", "name": n, "player": 1, "uuid": u, "tile": [0.5, 0.5]} for u, n in names.items()]
    server = FakeServer({u: {"Pos": p} for u, p in feet.items()} | {"Steve": {}})
    g = gather.Gather(server, grid([[64] * 40 for _ in range(40)], objects)).setup()
    g.selected = {"m-1", "v-1"}
    stance.open_menu(g, "Steve", "m-1")
    g.menus["Steve"]("Steve", stance.PATROL, False)
    monkeypatch.setattr(g.map, "pick_ground", lambda eye, d, reach=64: (20, 10))
    g.looks["Steve"] = ((0.0, 70.0, 0.0), (1.0, 0.0, 0.0))
    server.log.clear()
    return server, g


def test_the_menu_has_patrol_in_slot_6(monkeypatch):
    server, g = setup(monkeypatch)
    assert stance.PATROL == 6
    assert [name for slot, _, name, _ in stance.items(g, "m-1") if slot == stance.PATROL] == ["Patrol"]
    assert g.ordering == {"Steve": "patrol"}


def test_the_click_starts_a_patrol_of_the_military_units(monkeypatch):
    server, g = setup(monkeypatch)
    g.click("Steve")
    assert len(g.patrols) == 1
    tag, (b, a), leg = g.patrols[0]
    assert b[0] == 20 and b[2] == 10 and a[0] == 6 and leg == 0
    assert f"tag m-1 add {tag}" in server.log
    assert not any("tag v-1 add" in c for c in server.log)            # the villager does not patrol
    assert "aoe stance m-1 aggressive" in server.log
    assert f"aoe moveto @e[tag={tag}] {b[0]} {b[1]} {b[2]}" in server.log
    assert g.ordering == {}


def test_patrol_turns_the_units_back_at_the_point(monkeypatch):
    server, g = setup(monkeypatch)
    g.click("Steve")
    tag, (b, a), _ = g.patrols[0]
    real = g.command
    monkeypatch.setattr(g, "command", lambda c: "Test passed" if c.startswith("execute positioned") else real(c))
    server.log.clear()
    scenario.patrol(g)
    assert g.patrols[0][2] == 1
    assert f"aoe moveto @e[tag={tag}] {a[0]} {a[1]} {a[2]}" in server.log


def test_a_move_order_ends_the_patrol(monkeypatch):
    server, g = setup(monkeypatch)
    g.click("Steve")
    tag = g.patrols[0][0]
    server.log.clear()
    g.walk_to("Steve", (15, 15))
    assert f"tag m-1 remove {tag}" in server.log


def test_patrol_needs_no_patrols():
    g = type("G", (), {})()
    scenario.patrol(g)                                                 # a bare game: no command, no error
