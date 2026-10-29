"""game/follow.py: the stance menu has "Follow" (slot 8) and "Guard" (slot 9). The next right click on an own unit (or,
for Guard, an own building) gives the selected military units the order; follow.tick walks a far follower to its target,
a guard attacks an enemy near its target, and a dead target or a new order ends the entry (#3358)."""
from game import follow, gather, savegame, stance

from test_gather import FakeServer, grid


def setup(monkeypatch, slot, feet=None):
    """A militia (selected) and a villager of player 1 and an enemy militia of player 2; the menu item slot chosen."""
    feet = feet or {"m-1": (5.5, 64.0, 10.5), "v-1": (30.5, 64.0, 30.5), "e-1": (38.5, 64.0, 38.5)}
    names = {"m-1": ("MILITIA", 1), "v-1": ("VILLAGER_MALE", 1), "e-1": ("MILITIA", 2)}
    objects = [{"kind": "unit", "name": n, "player": p, "uuid": u, "tile": [0.5, 0.5]} for u, (n, p) in names.items()]
    server = FakeServer({u: {"Pos": p} for u, p in feet.items()} | {"Steve": {}})
    g = gather.Gather(server, grid([[64] * 40 for _ in range(40)], objects)).setup()
    g.selected = {"m-1"}
    stance.open_menu(g, "Steve", "m-1")
    g.menus["Steve"]("Steve", slot, False)
    where = dict(feet)
    monkeypatch.setattr(g, "positions", lambda uuids: {u: where[u] for u in uuids if u in where})
    g.looks["Steve"] = ((0.0, 70.0, 0.0), (1.0, 0.0, 0.0))
    server.log.clear()
    return server, g, where


def test_the_menu_has_follow_in_slot_8_and_guard_in_slot_9(monkeypatch):
    server, g, _ = setup(monkeypatch, stance.FOLLOW)
    assert (stance.FOLLOW, stance.GUARD) == (8, 9)
    names = {slot: name for slot, _, name, _ in stance.items(g, "m-1")}
    assert names[8] == "Follow" and names[9] == "Guard"
    assert g.ordering == {"Steve": "follow"}


def test_a_follow_of_an_own_unit_walks_the_unit_to_it(monkeypatch):
    server, g, where = setup(monkeypatch, stance.FOLLOW)
    monkeypatch.setattr(g, "target", lambda eye, d, places: ("unit", "v-1", set()))
    g.click("Steve")
    assert g.follows == {"m-1": ["v-1", "follow"]} and g.ordering == {}
    assert "aoe moveto m-1 30 64 30" in server.log
    server.log.clear()
    where["m-1"] = (31.5, 64.0, 31.5)                                  # near: no walk
    follow.tick(g)
    assert server.log == []


def test_a_click_on_the_ground_ends_the_pending_order(monkeypatch):
    server, g, _ = setup(monkeypatch, stance.FOLLOW)
    monkeypatch.setattr(g, "target", lambda eye, d, places: ("ground", (3, 3), {(3, 3)}))
    g.click("Steve")
    assert not getattr(g, "follows", {}) and g.ordering == {}
    assert any("actionbar" in c and "Follow" in c for c in server.log)


def test_a_guard_of_a_building_attacks_an_enemy_near_it(monkeypatch):
    server, g, where = setup(monkeypatch, stance.GUARD)
    monkeypatch.setattr(g, "target", lambda eye, d, places: ("building", (32, 40, 32, 40), set()))
    g.click("Steve")
    assert g.follows == {"m-1": [(32, 40, 32, 40), "guard"]}
    assert "aoe attack m-1 e-1" in server.log
    server.log.clear()
    where["e-1"] = (2.5, 64.0, 2.5)                                    # the enemy is far: walk back to the building
    follow.tick(g)
    assert server.log == ["aoe moveto m-1 36 64 36"]


def test_a_dead_target_and_a_move_order_end_the_entry(monkeypatch):
    server, g, where = setup(monkeypatch, stance.FOLLOW)
    monkeypatch.setattr(g, "target", lambda eye, d, places: ("unit", "v-1", set()))
    g.click("Steve")
    del where["v-1"]
    follow.tick(g)
    assert g.follows == {}
    g.follows = {"m-1": ["v-1", "follow"]}
    g.new_order({"m-1"})
    assert g.follows == {}


def test_a_save_and_a_load_keep_the_follows():
    assert "follows" in savegame.ORDERS
