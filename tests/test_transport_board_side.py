"""Land units board an own transport ship from the shore of their own land, not from a nearer shore across the sea
that they cannot walk to (#1694: the militia walked into the sea and sank to the sea floor)."""
import pytest
from test_gather import FakeServer, grid

from game import gather, transport


def setup(ship=15.5):
    """A 30 × 30 map (tile size 1): west land at x < 6, sea at x 6 to 19, east land at x >= 20. An own transport ship
    at (ship, 5.5) and two selected militia on the west land."""
    units = {"ship": ("TRANSPORT_SHIP", ship), "m": ("MILITIA", 2.5), "n": ("MILITIA", 3.5)}
    objects = [{"kind": "unit", "name": n, "player": 1, "uuid": u, "tile": [x, 5.5]} for u, (n, x) in units.items()]
    server = FakeServer({u: {"Pos": (x, 63.0 if u == "ship" else 64.0, 5.5)} for u, (_, x) in units.items()})
    g = gather.Gather(server, grid([[64] * 6 + ["-"] * 14 + [64] * 10 for _ in range(30)], objects), start={}).setup()
    g.paper = True
    g.choose({"m", "n"}, "m")
    return server, g


def test_the_units_board_from_their_own_shore_when_the_other_shore_is_nearer():
    server, g = setup()                                                # west shore 10 blocks, east shore 4.5 blocks
    assert transport.order(g, "Steve", "ship")
    assert g.loading == {"m": ("ship", (5, 5)), "n": ("ship", (5, 5))}
    assert any(c.startswith("aoe moveto m 5.5 ") for c in server.log)


def test_the_land_of_a_unit_ends_at_the_sea():
    server, g = setup()
    land = transport.body(g, (2, 5))
    assert len(land) == 6 * 30 and all(x < 6 for x, _ in land)
    assert transport.body(g, (10, 5)) == set()                         # a cell of the sea is no land


@pytest.mark.mc
def test_three_militia_board_a_ship_in_the_middle_of_the_sea_on_paper(tmp_path):
    """The setup of the check of #1492: a 48-tile map, sea at tiles x 14 to 33, 3 militia on the west land at x 10.5,
    the transport ship at x 24.5 (the east shore is nearer). All 3 go in within 30 s."""
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    import contextlib
    import io
    import json
    import time

    import scenarios
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
    from game import combat, run
    scn = scenarios.new_scenario(48)
    for t in scn.map_manager.terrain:
        if 14 <= t.x < 34:
            t.terrain_id = scenarios.TerrainId.WATER_DEEP
    um = scn.unit_manager
    um.add_unit(scenarios.PlayerId.ONE, UnitInfo.TRANSPORT_SHIP.ID, x=24.5, y=24.5)
    for y in (23.5, 24.5, 25.5):
        um.add_unit(scenarios.PlayerId.ONE, UnitInfo.MILITIA.ID, x=10.5, y=y)
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
        militia = {u for u, n in g.soldiers.items() if n == "MILITIA"}
        g.choose(set(militia), min(militia))
        assert transport.order(g, "nobody", ship)
        assert all(x < 14 * g.map.T for _, (x, _) in g.loading.values()), g.loading   # the west shore
        end = time.time() + 30
        while len(vars(g).get("cargo", {}).get(ship, [])) < 3:
            assert time.time() < end, ({u: g.pos(u) for u in militia}, g.pos(ship))
            g.step()
            time.sleep(g.tick)
