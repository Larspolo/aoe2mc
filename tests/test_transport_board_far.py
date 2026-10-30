"""Land units board an own transport ship far from the shore: the ship sails to the land cell nearest to it, and the
units go in there (#1653; the owner changed it in #2055: before, the ship stayed; the fake server tests are in
tests/test_transport_berth.py)."""
import pytest
from test_gather import FakeServer, grid

from game import gather, transport


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
    import math
    import time

    import scenarios
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
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
        assert after[0] < before[0] - 2 * g.map.T, (before, after)    # the ship sailed to the shore (#2055)
        assert any(not g.map.wet(math.floor(after[0]) - dx, math.floor(after[2])) for dx in range(1, 4)), after
        assert abs(inside[0] - after[0]) < 1 and abs(inside[2] - after[2]) < 1, (inside, after)   # the militia is in it
