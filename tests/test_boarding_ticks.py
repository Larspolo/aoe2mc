"""garrison.board_tick (a ram or a ship, #5225) and siege_tower.tick share the dict "boarding" of a Gather (#5555):
each tick takes only the units of its own holders. garrison.tick runs first and took the militia of a siege tower
into transport.go_in, so the tower never had its rider list."""
import types

import garrison
import siege_tower
import transport


def fake(boarding):
    pos = {"m": (50.0, 64.8, 50.0), "tower": (50.0, 64.3, 50.0), "s": (20.0, 64.0, 20.0), "ram": (20.0, 64.0, 21.0)}
    return types.SimpleNamespace(boarding=boarding, soldiers={"m": "MILITIA", "tower": siege_tower.NAME, "s": "MILITIA",
                                                              "ram": "BATTERING_RAM"},
                                 positions=lambda us: {u: pos[u] for u in us if u in pos}, paper=False)


def test_each_tick_takes_only_the_units_of_its_holders(monkeypatch):
    went = []
    monkeypatch.setattr(transport, "go_in", lambda g, u, h: went.append(("ram", u, h)))
    monkeypatch.setattr(siege_tower, "go_in", lambda g, u, h: went.append(("tower", u, h)))
    g = fake({"m": "tower", "s": "ram"})
    garrison.board_tick(g)
    assert went == [("ram", "s", "ram")] and g.boarding == {"m": "tower"}
    g = fake({"m": "tower", "s": "ram"})
    went.clear()
    siege_tower.tick(g)
    assert went == [("tower", "m", "tower")] and g.boarding == {"s": "ram"}


def test_a_dead_holder_ends_the_order():
    g = fake({"m": "gone"})
    garrison.board_tick(g)
    assert g.boarding == {}
