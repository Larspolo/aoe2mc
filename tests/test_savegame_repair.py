"""game/savegame.py: a save keeps the rally walk and the repair orders of the villagers (#2380, epic #2253): after the
load, a villager walks on to its rally point, and a repairer repairs on. Fake server, no Minecraft."""
import json

from test_repair import HOUSE, setup

from game import repair, savegame

RALLY = (20, 20)


def played():
    """v0 repairs the damaged house, v1 walks to its rally point."""
    server, g = setup(n=2)
    g.choose({"v0"}, "v0")
    assert repair.order(g, "Steve", (4, 5)) == HOUSE
    g.go(g.villagers["v1"], "to_rally", {RALLY})
    return server, g


def loaded(g):
    server, h = setup(n=2)
    savegame.load(h, json.loads(json.dumps(savegame.dump(g), sort_keys=True)))
    return server, h


def test_the_rally_walk_and_the_walk_to_the_repair_go_on():
    _, g = played()
    _, h = loaded(g)
    v0, v1 = h.villagers["v0"], h.villagers["v1"]
    assert (v0.state, h.repairs["v0"]) == ("to_repair", HOUSE) and v0.path
    assert v1.state == "to_rally" and v1.path and v1.path[-1] == RALLY


def test_the_repairer_repairs_on_the_next_tick():
    server, g = played()
    for _ in range(300):
        g.step()
        if g.villagers["v0"].state == "repair":
            break
    assert g.villagers["v0"].state == "repair"
    server, h = loaded(g)
    assert h.villagers["v0"].state == "repair" and h.repairs == {"v0": HOUSE}
    before = server.hp[repair.uuid(HOUSE)]
    for _ in range(10):
        h.step()
    assert server.hp[repair.uuid(HOUSE)] > before


def test_the_villager_at_its_rally_point_is_idle():
    _, g = played()
    for _ in range(300):
        g.step()
        if g.villagers["v1"].state == "idle":
            break
    assert loaded(g)[1].villagers["v1"].state == "idle"


def test_a_repair_of_a_building_that_is_gone_ends():
    _, g = played()
    d = savegame.dump(g)
    d["players"]["1"]["villagers"]["v0"]["repair"] = savegame.pack((0, 1, 0, 1))
    _, h = setup(n=2)
    savegame.load(h, json.loads(json.dumps(d)))
    assert h.villagers["v0"].state == "idle"
