"""Land units board an own transport ship without the ship sailing to the shore first: they walk to the land cell
nearest to the ship and go in from there, also when the ship is farther than SHORE tiles from the land (the owner's
check of #1492: "the units could teleport inside the ship iso the ship having to go to shore first", #1653)."""
import pytest
from test_gather import FakeServer, grid
from test_transport_ship import setup

from game import gather, transport


def moves(server, ship="ship"):
    return [c for c in server.log if c.split()[:2] in (["tp", ship], ["aoe", "moveto"]) and ship in c.split()[:3]]


@pytest.mark.parametrize("x", [15.5, 16.5, 20.5, 23.5])               # 2, 3, 7 and 10 tiles from the land (x < 14)
def test_the_units_board_from_the_nearest_shore_and_the_ship_stays(x):
    server, g = setup()                                                # tile size 1: SHORE is 3 blocks
    server.entities["ship"]["Pos"] = (x, 63.0, 5.5)
    assert transport.order(g, "Steve", "ship")
    assert g.loading == {u: ("ship", (13, 5)) for u in ("m", "s", "v")}
    for u in ("m", "s", "v"):
        server.entities[u]["Pos"] = (13.5, 64.0, 5.5)
    transport.tick(g)
    assert g.cargo == {"ship": ["m", "s", "v"]} and not g.loading
    assert "execute as ship on passengers run ride m mount @s" in server.log
    assert not moves(server) and not getattr(g.ships.get("ship"), "path", None) and server.entities["ship"]["Pos"] == (x, 63.0, 5.5)


def test_a_unit_on_the_way_does_not_go_in():
    server, g = setup()
    server.entities["ship"]["Pos"] = (20.5, 63.0, 5.5)
    assert transport.order(g, "Steve", "ship")
    server.entities["m"]["Pos"] = (9.5, 64.0, 5.5)                     # 4 blocks from the shore cell, 11 from the ship
    transport.tick(g)
    assert "m" in g.loading and "m" not in vars(g).get("cargo", {}).get("ship", [])


def test_no_land_on_the_map_no_boarding():
    objects = [{"kind": "unit", "name": n, "player": 1, "uuid": u, "tile": [x, 5.5]}
               for u, n, x in (("ship", "TRANSPORT_SHIP", 5.5), ("m", "MILITIA", 8.5))]
    server = FakeServer({o["uuid"]: {"Pos": (o["tile"][0], 63.0, 5.5)} for o in objects})
    g = gather.Gather(server, grid([["-"] * 12 for _ in range(12)], objects), start={}).setup()
    g.paper = True
    g.choose({"m"}, "m")
    assert not transport.order(g, "Steve", "ship")


@pytest.mark.mc
def test_a_militia_boards_a_ship_far_from_the_shore_on_paper(tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    import contextlib
    import io
    import json
    import time

    import aoe2mc
    import scenarios
    from AoE2ScenarioParser.datasets.units import UnitInfo

    from game import combat, run
    scn = scenarios.new_scenario(24)
    for t in scn.map_manager.terrain:                                   # a sea between two shores
        if 6 <= t.x < 18:
            t.terrain_id = scenarios.TerrainId.WATER_DEEP
    um = scn.unit_manager
    um.add_unit(scenarios.PlayerId.ONE, UnitInfo.TRANSPORT_SHIP.ID, x=11.5, y=12.5)   # 5 tiles from the land
    um.add_unit(scenarios.PlayerId.ONE, UnitInfo.MILITIA.ID, x=3.5, y=12.5)
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
        before = g.pos(ship)
        assert all(g.map.wet(x, z) for x in range(round(before[0]) - 3 * g.map.T, round(before[0]) + 3 * g.map.T)
                   for z in (round(before[2]),))                       # no land within SHORE tiles
        g.choose({militia}, militia)
        assert transport.order(g, "nobody", ship)
        end = time.time() + 60
        while not vars(g).get("cargo"):
            assert time.time() < end, (g.pos(militia), g.pos(ship))
            g.step()
            time.sleep(g.tick)
        time.sleep(1)
        assert "Test passed" in game.command(f"execute as {ship} on passengers if entity @s[nbt={{Passengers:[{{}}]}}]")
        after, inside = g.pos(ship), g.pos(militia)
        assert abs(after[0] - before[0]) < 1 and abs(after[2] - before[2]) < 1, (before, after)   # the ship stayed
        assert abs(inside[0] - after[0]) < 1 and abs(inside[2] - after[2]) < 1, (inside, after)   # the militia is in it
