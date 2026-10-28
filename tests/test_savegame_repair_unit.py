"""game/savegame.py: a villager that repairs a siege unit at the save repairs it on after the load (#2987, epic #2979).
Fake server, no Minecraft."""
import json

from test_repair_siege import RAM, setup

from game import repair, savegame


def loaded(g, hp):
    server, h = setup(hp=hp)
    savegame.load(h, json.loads(json.dumps(savegame.dump(g), sort_keys=True)))
    return server, h


def test_a_villager_that_repairs_a_ram_repairs_it_on_after_a_load():
    server, g = setup(hp=50.0)
    assert repair.unit_order(g, "Steve", "ram")
    while g.villagers["v0"].state != "repair":
        g.step()
    for _ in range(3):
        g.step()
    hp = server.health["ram"]
    assert hp > 50.0
    server_h, h = loaded(g, hp)
    for _ in range(3000):
        h.step()
    assert server_h.health["ram"] == RAM and h.villagers["v0"].state == "idle"


def test_a_villager_that_walks_to_the_ram_repairs_it_after_it_arrives():
    server, g = setup(hp=50.0)
    assert repair.unit_order(g, "Steve", "ram")
    g.step()
    assert g.villagers["v0"].state == "to_repair"
    server_h, h = loaded(g, 50.0)
    for _ in range(3000):
        h.step()
    assert server_h.health["ram"] == RAM


def test_a_ram_that_moves_after_the_load_stops_the_repair():
    _, g = setup(hp=50.0)
    assert repair.unit_order(g, "Steve", "ram")
    while g.villagers["v0"].state != "repair":
        g.step()
    g.step()
    server_h, h = loaded(g, 50.0)
    server_h.entities["ram"]["Pos"] = (14.5, 64.0, 12.5)
    before = server_h.health["ram"]
    for _ in range(50):
        h.step()
    assert server_h.health["ram"] == before and h.villagers["v0"].state == "idle"
