"""game/stance.py: the item "Auto Scout" of the stance menu is in slot 11 for a scout only. A click gives the selected
scouts the order (autoscout.start) and shows "Auto Scout" in the action bar (#3703)."""
from game import gather, stance

from test_gather import FakeServer, grid


def setup():
    """Two scouts and a militia of player 1 (all selected) on a 40 × 40 map."""
    feet = {"s-1": (5.5, 64.0, 5.5), "s-2": (9.5, 64.0, 9.5), "k-1": (12.5, 64.0, 12.5)}
    names = {"s-1": "SCOUT_CAVALRY", "s-2": "SCOUT_CAVALRY", "k-1": "MILITIA"}
    objects = [{"kind": "unit", "name": n, "player": 1, "uuid": u, "tile": [0.5, 0.5]} for u, n in names.items()]
    server = FakeServer({u: {"Pos": p} for u, p in feet.items()} | {"Steve": {}})
    g = gather.Gather(server, grid([[64] * 40 for _ in range(40)], objects)).setup()
    g.selected = {"s-1", "s-2", "k-1"}
    return server, g


def test_the_menu_of_a_scout_has_auto_scout_in_slot_11_and_the_menu_of_a_militia_has_none():
    server, g = setup()
    assert stance.AUTO_SCOUT == 11
    assert [name for slot, _, name, _ in stance.items(g, "s-1") if slot == stance.AUTO_SCOUT] == ["Auto Scout"]
    assert not [name for slot, _, name, _ in stance.items(g, "k-1") if slot == stance.AUTO_SCOUT]


def test_a_click_starts_the_order_for_the_selected_scouts_only_and_shows_it_in_the_action_bar():
    server, g = setup()
    stance.open_menu(g, "Steve", "s-1")
    server.log.clear()
    g.menus["Steve"]("Steve", stance.AUTO_SCOUT, False)
    assert set(g.scouting) == {"s-1", "s-2"}                              # the militia gets no order
    assert 'title Steve actionbar {"text": "Auto Scout"}' in server.log
    assert "aoe menu-close Steve" in server.log
