"""game/stance.py: the stance menu has an "Attack Move" item (slot 7). A click on it and then on a ground cell sends the
selected military units to the cell with the stance aggressive; each unit gets its old stance back at the point, and a
new order ends the attack move (AoE2 Attack Move, #3357)."""
from game import gather, stance

from test_gather import FakeServer, grid


def setup(monkeypatch):
    """A militia and a villager (player 1), both selected; Attack Move chosen in the menu; the next click hits (20, 10)."""
    feet = {"m-1": (5.5, 64.0, 10.5), "v-1": (12.5, 64.0, 4.5)}
    names = {"m-1": "MILITIA", "v-1": "VILLAGER_MALE"}
    objects = [{"kind": "unit", "name": n, "player": 1, "uuid": u, "tile": [0.5, 0.5]} for u, n in names.items()]
    server = FakeServer({u: {"Pos": p} for u, p in feet.items()} | {"Steve": {}})
    g = gather.Gather(server, grid([[64] * 40 for _ in range(40)], objects)).setup()
    g.selected = {"m-1", "v-1"}
    stance.open_menu(g, "Steve", "m-1")
    g.menus["Steve"]("Steve", stance.ATTACK_MOVE, False)
    monkeypatch.setattr(g.map, "pick_ground", lambda eye, d, reach=64: (20, 10))
    g.looks["Steve"] = ((0.0, 70.0, 0.0), (1.0, 0.0, 0.0))
    server.log.clear()
    return server, g


def test_the_menu_has_attack_move_in_slot_7(monkeypatch):
    server, g = setup(monkeypatch)
    assert stance.ATTACK_MOVE == 7
    assert [name for slot, _, name, _ in stance.items(g, "m-1") if slot == stance.ATTACK_MOVE] == ["Attack Move"]
    assert g.ordering == {"Steve": "attack_move"}


def test_the_click_sends_the_military_units_to_the_point_aggressive(monkeypatch):
    server, g = setup(monkeypatch)
    g.click("Steve")
    assert "aoe stance m-1 aggressive" in server.log
    assert any(c.startswith("aoe moveto m-1 ") for c in server.log)
    assert not any("v-1" in c for c in server.log)                     # the villager gets no command
    assert g.attack_moves["m-1"][0] == (20, 10) and g.attack_moves["m-1"][1] == "aggressive"
    assert g.ordering == {}


def test_a_defensive_unit_gets_its_stance_back_at_the_point(monkeypatch):
    server, g = setup(monkeypatch)
    g.stances = {"m-1": "defensive"}
    g.click("Steve")
    assert "aoe stance m-1 aggressive" in server.log and g.stances == {}
    server.log.clear()
    where = {"m-1": (5.5, 64.0, 10.5)}                                # still on its way: nothing yet
    monkeypatch.setattr(g, "positions", lambda uuids: {u: where[u] for u in uuids if u in where})
    stance.arrive(g)
    assert server.log == [] and "m-1" in g.attack_moves
    where["m-1"] = (20.5, 64.0, 10.5)                                  # at the point
    stance.arrive(g)
    assert "aoe stance m-1 defensive" in server.log and g.stances == {"m-1": "defensive"}
    assert g.attack_moves == {}


def test_a_new_order_ends_the_attack_move(monkeypatch):
    server, g = setup(monkeypatch)
    g.stances = {"m-1": "defensive"}
    g.click("Steve")
    server.log.clear()
    g.new_order({"m-1"})
    assert "aoe stance m-1 defensive" in server.log and g.attack_moves == {}
