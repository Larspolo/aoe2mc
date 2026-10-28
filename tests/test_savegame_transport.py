"""game/savegame.py: a save keeps the units inside the transport ships and the siege towers and the units on the way
to them (#2411, epic #2253). Fake server, no Minecraft."""
import json

from test_transport_ship import setup

from game import savegame, siege_tower, transport


def played():
    """2 units in the transport ship, the villager on the way to it, 1 unit in a siege tower and 1 on the way to it."""
    server, g = setup()
    server.entities["tower"] = {"Pos": (8.5, 64.0, 12.5)}
    g.soldiers["tower"] = siege_tower.NAME
    g.cargo, g.loading, g.berths = {"ship": ["m", "s"]}, {"v": ("ship", (13, 5))}, {"ship": (14, 5)}
    g.towers, g.boarding = {"tower": ["x"]}, {"y": "tower"}
    return g


def loaded(g):
    server, h = setup()
    server.entities["tower"] = {"Pos": (8.5, 64.0, 12.5)}
    server.log.clear()
    savegame.load(h, json.loads(json.dumps(savegame.dump(g), sort_keys=True)))
    return server, h


def test_a_loaded_game_keeps_the_units_inside_and_on_the_way():
    g = played()
    server, h = loaded(g)
    for f in ("cargo", "loading", "berths", "towers", "boarding"):
        assert vars(h)[f] == vars(g)[f], f
    assert any(c.startswith("aoe moveto v 13.5 64") for c in server.log)     # the villager walks to the ship again
    assert "aoe moveto y 8.5 64.0 12.5" in server.log                      # and the unit to the tower
    server.log.clear()
    assert transport.out(h, "ship") == ["m", "s"] and "ride s dismount" in server.log and "ride m dismount" in server.log


def test_a_save_from_before_has_no_transport_keys():
    server, g = setup()
    d = savegame.dump(g)
    assert not {"cargo", "loading", "towers", "boarding"} & set(d["players"]["1"])
    server, h = loaded(g)
    assert not {"cargo", "loading", "towers", "boarding"} & set(vars(h))
    assert not any(c.startswith("aoe moveto") for c in server.log)
