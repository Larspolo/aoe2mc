"""game/train.py: a right click on a unit item sets the auto-queue of the building, as in AoE2 DE (#3524): the
building trains the unit again each time its queue is empty and the resources are there; a second right click stops it."""
from test_train_barracks import setup

from game import train

RECT = (10, 13, 2, 5)                                                  # the barracks of setup()


def run(g, server, seconds):
    """Run the queues for AoE2 seconds; each trained unit also exists on the FakeServer. Returns the new units."""
    out = []
    for _ in range(round(seconds / 0.5)):
        for v in train.tick(g, 0.5):
            server.entities[getattr(v, "uuid", v)] = {"Pos": (11.5, 64.0, 6.5)}
            out.append(v)
    return out


def right(g, slot=0):
    """A right click on the item in slot of the open barracks menu."""
    g.menus["Steve"]("Steve", slot, False, right=True)


def test_a_right_click_trains_militia_while_the_resources_last():
    server, g = setup(food=0, gold=0)
    cost, t = train.price(g, "MILITIA"), train.seconds(g, "MILITIA", "BARRACKS") + 1
    g.stock.update({r: 3 * v for r, v in cost.items()})
    train.open_menu(g, "Steve", (11, 3))
    right(g)
    assert g.auto == {RECT: "MILITIA"} and "Auto-queue%3A%20on" in server.log[-1]
    assert len(run(g, server, 4 * t)) == 3 and not g.queues[RECT]      # 3 militia, then it waits
    assert not any(g.stock[r] for r in cost) and g.auto == {RECT: "MILITIA"}
    g.stock.update(cost)
    assert len(run(g, server, t)) == 1
    right(g)                                                           # a second right click stops it
    assert not g.auto
    g.stock.update(cost)
    assert not run(g, server, t) and all(g.stock[r] == v for r, v in cost.items())


def test_it_waits_at_the_population_limit(monkeypatch):
    server, g = setup(food=500, gold=500)
    train.open_menu(g, "Steve", (11, 3))
    right(g)
    monkeypatch.setattr(train, "limit", lambda g: g.pop)               # no population room
    t = train.seconds(g, "MILITIA", "BARRACKS") + 1
    assert not run(g, server, t) and len(g.queues[RECT]) == 1         # one militia waits in the queue
    monkeypatch.setattr(train, "limit", lambda g: g.pop + 1)          # a new house
    assert len(run(g, server, t)) == 1


def test_a_cancel_and_a_fallen_building_end_it():
    server, g = setup(food=500, gold=500)
    train.open_menu(g, "Steve", (11, 3))
    right(g)
    train.tick(g, 0.5)
    train.cancel(g, "Steve", RECT, 0)
    assert not g.auto
    right(g)
    g.sites.clear()                                                    # the barracks is gone
    train.tick(g, 0.5)
    assert not g.auto


def test_a_normal_click_does_not_set_it():
    server, g = setup()
    train.open_menu(g, "Steve", (11, 3))
    g.menus["Steve"]("Steve", 0, False)
    assert not vars(g).get("auto") and len(g.queues[RECT]) == 1


def test_a_save_keeps_it():
    from game import savegame
    server, g = setup()
    train.open_menu(g, "Steve", (11, 3))
    right(g)
    d = savegame.unpack(savegame.pack(savegame.dump(g)))["players"]["1"]
    assert d["auto"] == {RECT: "MILITIA"} and d["auto_by"] == {RECT: "Steve"}
