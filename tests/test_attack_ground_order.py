"""game/stance.py: the stance menu has an "Attack Ground" item (slot 12). A click on it and then on a ground cell lets
the selected siege units shoot at that point (`aoe attackground`, #4078); the other units ignore it (#4079)."""
from game import gather, hints, stance

from test_gather import FakeServer, grid


def setup(monkeypatch, names):
    """The units names (uuid -> AoE2 name) of player 1, all selected; Attack Ground chosen; the next click hits (20, 10)."""
    server = FakeServer({u: {"Pos": (5.5 + i, 64.0, 10.5)} for i, u in enumerate(names)} | {"Steve": {}})
    objects = [{"kind": "unit", "name": n, "player": 1, "uuid": u, "tile": [0.5, 0.5]} for u, n in names.items()]
    g = gather.Gather(server, grid([[64] * 40 for _ in range(40)], objects)).setup()
    g.selected = set(names)
    server.log.clear()
    stance.open_menu(g, "Steve", next(iter(names)))
    g.menus["Steve"]("Steve", stance.ATTACK_GROUND, False)
    monkeypatch.setattr(g.map, "pick_ground", lambda eye, d, reach=64: (20, 10))
    g.looks["Steve"] = ((0.0, 70.0, 0.0), (1.0, 0.0, 0.0))
    return server, g


def test_the_mangonel_shoots_at_the_point_and_the_militia_gets_nothing(monkeypatch):
    server, g = setup(monkeypatch, {"o-1": "MANGONEL", "m-1": "MILITIA"})
    assert stance.ATTACK_GROUND == 12
    assert [name for slot, _, name, _ in stance.items(g, "o-1") if slot == stance.ATTACK_GROUND] == ["Attack Ground"]
    assert g.ordering == {"Steve": "attack_ground"}
    assert hints.state(g, "Steve") == ("attack_ground", hints.TEXTS["attack_ground"])
    server.log.clear()
    g.click("Steve")
    assert f"aoe attackground o-1 20 {g.map.y(20, 10)} 10" in server.log
    assert not any("m-1" in c for c in server.log)
    assert g.ordering == {}


def test_a_selection_with_no_siege_unit_gives_the_hint_and_no_command(monkeypatch):
    server, g = setup(monkeypatch, {"m-1": "MILITIA"})
    assert any("No unit can attack the ground" in c for c in server.log)
    assert not vars(g).get("ordering")
    server.log.clear()
    g.click("Steve")
    assert not any("attackground" in c for c in server.log)
