"""game/transport.py: the dock trains the transport ship, up to 20 land units ride it and come out on the land
nearest to the ship or to a clicked land cell (#1385). Fake server; an mc test on Paper."""
import math
import time

import pytest
from test_dock_train import dock_map
from test_gather import FakeServer, grid
from test_train_archery import menus

from game import combat, fleet, garrison, gather, run, train, transport

UNITS = {"ship": ("TRANSPORT_SHIP", 15.5, 5.5), "f": ("FISHING_SHIP", 16.5, 9.5), "m": ("MILITIA", 10.5, 5.5),
         "s": ("SCOUT_CAVALRY", 11.5, 6.5), "v": ("VILLAGER_MALE", 9.5, 5.5)}


def setup():
    """A flat 24 × 24 map (tile size 1): land at x < 14 (y 64), water at x >= 14. An own transport ship at (15.5, 5.5)
    and a fishing ship on the water, a militia, a scout cavalry and a villager on the land. All but the transport ship
    are selected."""
    objects = [{"kind": "unit", "name": n, "player": 1, "uuid": u, "tile": [x, z]} for u, (n, x, z) in UNITS.items()]
    ents = {o["uuid"]: {"Pos": (o["tile"][0], 63.0 if o["tile"][0] > 14 else 64.0, o["tile"][1])} for o in objects}
    server = FakeServer(ents)
    g = gather.Gather(server, grid([[64] * 14 + ["-"] * 10 for _ in range(24)], objects), start={}).setup()
    g.paper = True
    g.choose({"f", "m", "s", "v"}, "m")
    return server, g


def test_the_dock_trains_the_transport_ship_with_the_aoe2_values():
    assert (train.COSTS["TRANSPORT_SHIP"], train.TRAIN_TIMES["TRANSPORT_SHIP"]) == ({"wood": 125}, 46)   # AoE2 DE wiki
    assert combat.stats("TRANSPORT_SHIP")[:4] == (70, 0, 0, 2) and transport.SIZE == 20
    assert fleet.speed("TRANSPORT_SHIP", 4) == pytest.approx(1.45 * 4)
    server, g = dock_map()
    rect = train.open_menu(g, "Steve", (15, 12))
    assert "2:spruce_chest_boat:Transport Ship:125 wood · 46 s · queue 0/15" in menus(server)[-1]
    assert train.order(g, "Steve", rect, 2) == 1 and g.stock["wood"] == 75
    uuid, = train.tick(g, 46)
    assert g.soldiers[uuid] == "TRANSPORT_SHIP" and uuid in g.ships


def test_land_units_walk_to_the_shore_and_ride_the_ship():
    server, g = setup()
    assert transport.order(g, "Steve", "ship")
    assert g.loading == {"m": ("ship", (13, 5)), "s": ("ship", (13, 5)), "v": ("ship", (13, 5))}   # not the ship "f"
    assert any(c.startswith("aoe moveto m 13.5 64") for c in server.log)
    for u in ("m", "s", "v"):
        server.entities[u]["Pos"] = (13.5, 64.0, 5.5)
    server.log.clear()
    transport.tick(g)
    i = server.log.index
    assert i("execute as ship on passengers run ride m mount @s") < i("ride s mount m") \
        < i("execute as s on passengers run ride v mount @s")         # a horse takes one rider: on its rider
    assert f"data merge entity v {garrison.INSIDE}" in server.log and "aoe hide @a s" in server.log
    assert g.holds == {"ship": ["m", "s", "v"]} and not g.loading
    assert {"m", "s", "v"} <= garrison.inside(g) and g.selected == {"f"} and g.villagers["v"].state == "garrison"


def test_a_full_ship_takes_no_more():
    server, g = setup()
    g.holds = {"ship": [f"x{k}" for k in range(19)]}
    transport.order(g, "Steve", "ship")
    for u in ("m", "s"):
        server.entities[u]["Pos"] = (14.0, 64.0, 5.5)                   # next to the ship
    transport.tick(g)
    assert g.holds["ship"][-1] == "m" and len(g.holds["ship"]) == 20 and "s" not in garrison.inside(g)


def test_a_click_on_the_selected_ship_unloads_it_on_the_nearest_land():
    server, g = setup()
    g.holds = {"ship": ["m", "s"]}
    server.log.clear()
    assert transport.out(g, "ship") == ["m", "s"] and not g.holds
    tps = [c.split() for c in server.log if c.startswith("tp ")]
    assert [t[1] for t in tps] == ["s", "m"] and tps[0][2:] == ["13.5", "64", "5.5"]   # the top of the stack first
    assert all(g.map.free(math.floor(float(t[2])), math.floor(float(t[4]))) for t in tps)
    assert server.log[1] == "ride s dismount" and f"data merge entity m {garrison.OUTSIDE}" in server.log
    server.entities["ship"]["Pos"] = (22.5, 63.0, 20.5)                 # far from the land: they stay inside
    g.holds = {"ship": ["m"]}
    assert transport.out(g, "ship") == [] and g.holds == {"ship": ["m"]}


def test_a_loaded_ship_sent_to_the_land_unloads_there_after_the_trip():
    server, g = setup()
    g.holds = {"ship": ["m", "v"]}
    g.choose({"ship"}, "ship")
    out = g.walk_to("Steve", (12, 15))
    assert g.map.wet(*out["ship"]) and g.unloads == {"ship": (12, 15)}
    transport.tick(g)
    assert g.holds                                                      # it sails first
    for _ in range(30):
        fleet.tick(g, 1.0)
    transport.tick(g)
    assert not g.holds and not g.unloads
    tps = [c.split() for c in server.log if c.startswith("tp ")]
    assert {(math.floor(float(t[2])), math.floor(float(t[4]))) for t in tps} == {(12, 15), (11, 15)}
    g.holds = {"ship": ["m"]}
    g.walk_to("Steve", (20, 20))                                       # onto the water: no unload
    assert not g.unloads


def test_the_units_of_a_sunk_ship_are_lost():
    server, g = setup()
    g.holds = {"ship": ["m", "v"]}
    del g.soldiers["ship"]
    transport.tick(g)
    assert not g.holds and {"kill m", "kill v"} <= set(server.log)


@pytest.mark.mc
def test_a_militia_rides_a_transport_ship_to_another_shore_on_paper(tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    import contextlib
    import io
    import json

    import aoe2mc
    import scenarios
    from AoE2ScenarioParser.datasets.units import UnitInfo
    scn = scenarios.new_scenario(24)
    for t in scn.map_manager.terrain:                                   # a sea between two shores
        if 8 <= t.x < 16:
            t.terrain_id = scenarios.TerrainId.WATER_DEEP
    um = scn.unit_manager
    um.add_unit(scenarios.PlayerId.ONE, UnitInfo.TRANSPORT_SHIP.ID, x=9.5, y=12.5)
    um.add_unit(scenarios.PlayerId.ONE, UnitInfo.MILITIA.ID, x=5.5, y=12.5)
    src = str(tmp_path / "s.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        combat.setup(game, data)
        g = gather.Gather(game, data, tick=0.25, start={}).setup()
        ship, = [u for u, n in g.soldiers.items() if n == "TRANSPORT_SHIP"]
        militia, = [u for u, n in g.soldiers.items() if n == "MILITIA"]
        g.choose({militia}, militia)
        assert transport.order(g, "nobody", ship)
        end = time.time() + 60
        while not vars(g).get("holds"):
            assert time.time() < end, (g.pos(militia), g.pos(ship))
            g.step()
            time.sleep(g.tick)
        assert "Test passed" in game.command(f"execute as {ship} on passengers if entity @s[nbt={{Passengers:[{{}}]}}]")
        T = g.map.T
        goal = (17 * T + 1, 12 * T + 1)                                  # a land cell on the east shore
        assert g.map.free(*goal)
        g.choose({ship}, ship)
        assert ship in g.walk_to("nobody", goal) and g.unloads
        end = time.time() + 90
        while vars(g).get("holds"):
            assert time.time() < end, (g.pos(ship), g.ships[ship].path[-1:])
            g.step()
            time.sleep(g.tick)
        time.sleep(1)
        pos = g.pos(militia)
        assert math.dist((pos[0], pos[2]), goal) < 2 * T and g.map.free(math.floor(pos[0]), math.floor(pos[2])), pos
        assert game.command(f"data get entity {militia} Invulnerable").strip().endswith("0b")
