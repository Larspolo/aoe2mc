"""game/garrison.py: the menu item "Ring Town Bell" of an own town center sends each own villager into the nearest own
building with room, as in AoE2 DE (#3419)."""
import json

from menu_line import item
from test_garrison_game import TC, TOWER, arrive, setup
from test_lang_orders import plain_log
from test_train_menu import menus

from game import garrison, lang, train


def ring(server, g):
    train.open_menu(g, "Steve", (3, 3))
    train.order(g, "Steve", TC, garrison.BELL[0])


def test_the_town_center_menu_has_the_bell_in_slot_24():
    server, g = setup()
    train.open_menu(g, "Steve", (3, 3))
    assert item(menus(server)[-1], "Ring Town Bell") == "24:bell:Ring Town Bell:Click: all villagers seek shelter"


def test_the_bell_sends_the_villagers_to_the_nearest_building_and_a_far_one_keeps_working():
    server, g = setup(villagers=8)
    server.entities["v7"]["Pos"] = (22.5, 64.0, 22.5)              # far from all own buildings
    g.soldiers["m0"] = "MILITIA"
    server.entities["m0"] = {"Pos": (5.5, 64.0, 9.5)}
    ring(server, g)
    tc, tower = garrison.door(g, TC), garrison.door(g, TOWER)
    assert set(g.entering) == {f"v{k}" for k in range(7)} and "m0" not in g.entering and g.villagers["v7"].state != "garrison"
    for u, rect in g.entering.items():
        x, _, z = server.entities[u]["Pos"]
        d = {r: (x - door[0] - 0.5) ** 2 + (z - door[1] - 0.5) ** 2 for r, door in [(TC, tc), (TOWER, tower)]}
        assert rect == min(d, key=d.get), u
    assert TC in g.entering.values() and TOWER in g.entering.values()
    assert "playsound minecraft:block.bell.use master Steve" in server.log
    assert any("The town bell rings: 7 villagers seek shelter" in c for c in plain_log(server.log))
    for rect in (TC, TOWER):
        arrive(server, g, rect)
    assert sorted(u for us in g.garrisons.values() for u in us) == [f"v{k}" for k in range(7)]


def test_a_full_tower_sends_the_rest_to_the_town_center():
    server, g = setup(villagers=8)
    for k in range(8):
        server.entities[f"v{k}"]["Pos"] = (9.5, 64.0, 5.5)        # all next to the tower door
    ring(server, g)
    room = garrison.size(g, "WATCH_TOWER")
    assert sum(r == TOWER for r in g.entering.values()) == room and sum(r == TC for r in g.entering.values()) == 8 - room


def test_with_no_villager_the_bell_only_says_so():
    server, g = setup(villagers=0)
    ring(server, g)
    assert not g.entering
    assert "tellraw Steve " + json.dumps(lang.text("aoe2mc.garrison.no_villagers", color="gray")) in server.log
