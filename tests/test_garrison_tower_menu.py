"""game/garrison.py: a right click on an own tower, keep or house with units inside opens a menu with the item
UNGARRISON, which lets them out. Only buildings with no training menu (#2970)."""
from menu_line import item
from test_garrison_game import TOWER, arrive, setup
from test_gather import FakeServer, grid
from test_train_menu import menus

import civs
from game import build, garrison, gather, train

UNGARRISON = "7:oak_door:Ungarrison:Click: all units come out"


def right_click(server, g):
    """One right click of Steve (a stick use after the hold time, as in tests/test_garrison_game.py)."""
    now = [0.0]
    g.clock = lambda: now[0]
    server.scores["aoe_use"] = 1
    assert g.clicks() == []
    now[0] = gather.HOLD
    for name in g.clicks():
        g.click(name)


def aim_at_the_tower(server):
    """Steve stands 2 blocks east of the tower and looks at it (docs/research/gameplay.md, "put the eye 2 blocks up")."""
    server.entities["Steve"] |= {"Pos": (11.0, 66.0, 9.5), "Rotation": (180, 29.1)}


def tower_with_two_villagers():
    server, g = setup()
    g.choose({"v0", "v1"}, "v0")
    garrison.order(g, "Steve", (11, 3))
    arrive(server, g, TOWER)
    g.choose(set(), None)
    aim_at_the_tower(server)
    return server, g


def test_a_right_click_on_an_own_tower_with_units_inside_opens_the_ungarrison_menu():
    server, g = tower_with_two_villagers()
    right_click(server, g)
    cmd = menus(server)[-1]
    assert cmd.startswith("aoe menu Steve Watch Tower ") and item(cmd, "Ungarrison") == UNGARRISON
    assert "Steve" in g.menus and g.garrisons[TOWER] == ["v0", "v1"]


def test_the_ungarrison_item_lets_the_units_out_next_to_the_door_and_closes_the_menu():
    server, g = tower_with_two_villagers()
    right_click(server, g)
    server.scores["aoe_menu"] = 8                                      # slot 7
    g.clicks()
    assert not g.garrisons.get(TOWER) and "aoe menu-close Steve" in server.log and "Steve" not in g.menus
    ring = g.map.front(TOWER)
    for k, u in enumerate(["v0", "v1"]):
        x, z = ring[k]
        assert f"tp {u} {x + 0.5} 64 {z + 0.5}" in server.log and g.villagers[u].state == "idle"
        assert f"tag {u} remove aoe2mc.garrisoned" in server.log


def test_an_own_tower_with_no_units_inside_opens_only_the_delete_menu():
    server, g = setup()
    aim_at_the_tower(server)
    right_click(server, g)
    assert "Ungarrison" not in " ".join(menus(server)) and "Delete" in menus(server)[-1]   # demolish.py (#3452)


def test_a_right_click_with_a_selection_on_the_tower_is_still_a_garrison_order():
    server, g = tower_with_two_villagers()
    g.choose({"v0"}, "v0")
    right_click(server, g)
    assert "v0" in g.entering and not menus(server)


def test_each_holder_without_a_training_menu_has_the_item_when_units_are_inside(monkeypatch):
    names = sorted((set(garrison.SIZES) | {b for c in civs.GARRISON.values() for b in c}) - set(train.TRAINS))
    assert names and "WATCH_TOWER" in names
    monkeypatch.setattr(civs, "civ", lambda g, player=None: "KHMER")   # the Khmer house takes 5 units (civs.GARRISON)
    objects = [{"kind": "building", "name": n, "player": 1, "tile": [2 * k + 1, 1], "footprint": [2 * k, 0, 2 * k + 2, 2],
                "ref": k} for k, n in enumerate(names)]
    objects += [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v0", "tile": [1.5, 9.5]}]
    server = FakeServer({"v0": {"Pos": (1.5, 64.0, 9.5)}, "Steve": {"Pos": (1.5, 66.0, 9.5), "Rotation": (180, 29.1)}})
    g = gather.Gather(server, grid([[64] * 2 * len(names) + [64] * 2 for _ in range(4)], objects)).setup()
    g.paper = True
    for k, n in enumerate(names):
        rect = (2 * k, 2 * k + 2, 0, 2)
        g.garrisons = {rect: ["v0"]}
        assert garrison.open_menu(g, "Steve", (2 * k, 0)) == rect, n
        cmd = menus(server)[-1]
        assert cmd.startswith(f"aoe menu Steve {build.pretty(n)} ") and item(cmd, "Ungarrison") == UNGARRISON, n
    assert len(menus(server)) == len(names)
