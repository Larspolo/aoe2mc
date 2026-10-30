"""game/stance.py: the stance menu has a "Stop" item (slot 5) that stops the selected military units at once and ends
their patrol (AoE2 Stop, #3353). A villager in the selection gets no command."""
from test_gather import FakeServer, grid

from game import gather, stance


def setup():
    """A militia and a villager (player 1), both selected."""
    feet = {"m-1": (5.5, 64.0, 10.5), "v-1": (12.5, 64.0, 4.5)}
    names = {"m-1": "MILITIA", "v-1": "VILLAGER_MALE"}
    objects = [{"kind": "unit", "name": n, "player": 1, "uuid": u, "tile": [0.5, 0.5]} for u, n in names.items()]
    server = FakeServer({u: {"Pos": p} for u, p in feet.items()} | {"Steve": {}})
    g = gather.Gather(server, grid([[64] * 40 for _ in range(40)], objects)).setup()
    g.selected = {"m-1", "v-1"}
    return server, g


def test_the_menu_has_stop_in_slot_5():
    server, g = setup()
    assert stance.STOP == 5
    assert [name for slot, _, name, _ in stance.items(g, "m-1") if slot == stance.STOP] == ["Stop"]
    stance.open_menu(g, "Steve", "m-1")
    assert any("Stop" in c for c in server.log)


def test_stop_sends_aoe_stop_to_the_military_units_only():
    server, g = setup()
    stance.open_menu(g, "Steve", "m-1")
    server.log.clear()
    g.menus["Steve"]("Steve", stance.STOP, False)
    assert "aoe stop m-1" in server.log
    assert not any("v-1" in c for c in server.log)                       # no command to the villager
    assert "aoe menu-close Steve" in server.log                          # the menu closes


def test_stop_ends_the_patrol_of_a_unit():
    server, g = setup()
    g.patrols = [("walk-1", 0, 0)]
    stance.open_menu(g, "Steve", "m-1")
    server.log.clear()
    g.menus["Steve"]("Steve", stance.STOP, False)
    assert "tag m-1 remove walk-1" in server.log
