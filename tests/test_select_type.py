"""game/gather.py: a second click on a selected military unit opens the stance menu (#1107); its last item selects all
own units of its type near it (#743)."""
from test_gather import FakeServer, grid
from test_gather_attack import click

from game import gather, stance


def setup():
    """Three militia near each other, one militia 30 blocks away, an archer and a villager (player 1)."""
    feet = {"m-1": (5.5, 64.0, 10.5), "m-2": (8.5, 64.0, 12.5), "m-3": (3.5, 64.0, 16.5), "m-far": (35.5, 64.0, 10.5),
            "a-1": (7.5, 64.0, 8.5), "v-1": (12.5, 64.0, 4.5)}
    names = {"m-1": "MILITIA", "m-2": "MILITIA", "m-3": "MILITIA", "m-far": "MILITIA", "a-1": "ARCHER",
             "v-1": "VILLAGER_MALE"}
    objects = [{"kind": "unit", "name": n, "player": 1, "uuid": u, "tile": [0.5, 0.5]} for u, n in names.items()]
    server = FakeServer({u: {"Pos": p} for u, p in feet.items()} | {"Steve": {}})
    return server, gather.Gather(server, grid([[64] * 40 for _ in range(40)], objects)).setup()


def test_a_second_click_selects_the_militia_near_it():
    server, g = setup()
    click(server, g, (5.5, 13.5), (5.5, 10.5))
    assert g.selected == {"m-1"}
    log = click(server, g, (5.5, 13.5), (5.5, 10.5))
    assert g.selected == {"m-1"} and "Steve" in g.menus               # the stance menu
    g.menus["Steve"]("Steve", stance.TYPE, False)
    assert g.selected == {"m-1", "m-2", "m-3"}                         # not the archer, not the far militia
    assert all(f"tag {u} add {gather.SELECT}" in log for u in ("m-2", "m-3"))
    assert not any(u in c for c in log for u in ("a-1", "m-far") if "add" in c)


def test_other_units_leave_the_selection():
    server, g = setup()
    click(server, g, (7.5, 5.5), (7.5, 8.5))                           # the archer
    click(server, g, (5.5, 13.5), (5.5, 10.5))                         # a militia: added
    assert g.selected == {"a-1", "m-1"}
    log = click(server, g, (5.5, 13.5), (5.5, 10.5))
    g.menus["Steve"]("Steve", stance.TYPE, False)
    assert g.selected == {"m-1", "m-2", "m-3"}
    assert f"tag a-1 remove {gather.SELECT}" in log and "data merge entity a-1 {Glowing:0b}" in log


def test_a_second_click_on_a_villager_still_opens_the_build_menu(monkeypatch):
    server, g = setup()
    opened = []
    monkeypatch.setattr(gather.build, "open_menu", lambda g, name: opened.append(name))
    click(server, g, (12.5, 7.5), (12.5, 4.5))
    assert g.selected == {"v-1"} and not opened
    click(server, g, (12.5, 7.5), (12.5, 4.5))
    assert opened == ["Steve"] and g.selected == {"v-1"}
