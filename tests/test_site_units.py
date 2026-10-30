"""game/build.py: a new construction site moves the units on its footprint to the nearest free cell next to it, as in
AoE2 (#1769): else the blocks of the site suffocate them."""
import contextlib
import io
import json
import time

import pytest
from test_gather import FakeServer, grid

from game import build, gather, run


def test_a_new_site_moves_a_unit_on_its_footprint_out():
    data = grid([[64] * 24 for _ in range(24)], [])
    data["objects"] += [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v0"},
                        {"kind": "unit", "name": "MILITIA", "player": 1, "uuid": "m0"}]
    data.update(level_height=1, players={"1": {"color": "blue", "arch": "western"}})
    server = FakeServer({"v0": {"Pos": (11.5, 64.0, 10.5)}, "m0": {"Pos": (11.3, 64.0, 6.5)}})
    g = gather.Gather(server, data).setup()
    g.stock.update(wood=200)
    build.found(g, "HOUSE", (8, 12, 8, 12))
    assert not [c for c in server.log if c.startswith("tp m0")]         # off the footprint: it stays
    assert "tp v0 12.5 64 10.5" in server.log                           # x = 12 is the free cell east of x = 11
    assert g.villagers["v0"].pos == (12.5, 64.0, 10.5)


def test_a_unit_in_the_middle_goes_to_the_nearest_side():
    data = grid([[64] * 24 for _ in range(24)], [])
    data["objects"].append({"kind": "unit", "name": "MILITIA", "player": 1, "uuid": "m0"})
    data.update(level_height=1, players={"1": {"color": "blue", "arch": "western"}})
    server = FakeServer({"m0": {"Pos": (9.4, 64.0, 10.8)}})
    g = gather.Gather(server, data).setup()
    g.stock.update(wood=200)
    g.map.blocked.add((7, 10))                                          # the west cell next to it is not free
    moved = build.clear(g, {(x, z) for x in range(8, 12) for z in range(8, 12)})
    assert moved == {"m0": (9, 12)}                                     # south: 1.7 blocks, west (7, 10) blocked
    assert "tp m0 9.5 64 12.5" in server.log


@pytest.mark.mc
def test_a_unit_on_a_new_site_lives_outside_it_on_a_server(tmp_path):
    from test_damage import health
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    import scenarios
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
    scn = scenarios.new_scenario(24)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=2.5, y=2.5)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, UnitInfo.MILITIA.ID, x=9.5, y=9.5)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, UnitInfo.SCOUT_CAVALRY.ID, x=8.5, y=9.5)   # a rider on a horse
    src = str(tmp_path / "site.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        g = gather.Gather(game, data, tick=0.25, start={}).setup()
        g.stock.update(wood=500)
        m, = [o["uuid"] for o in data["objects"] if o["kind"] == "unit" and o["name"] == "MILITIA"]
        c, = [o["uuid"] for o in data["objects"] if o["kind"] == "unit" and o["name"] == "SCOUT_CAVALRY"]
        game.command(f"tag {m} add m")
        game.command(f"data merge entity {m} {{NoAI:1b}}")             # it does not walk back
        x, y, z = g.pos(m)
        T, s = g.map.T, build.footprint("MILL")
        tx, tz = int(x) // T - s // 2, int(z) // T - s // 2
        rect = (tx * T, (tx + s) * T, tz * T, (tz + s) * T)
        assert rect[0] <= x < rect[1] and rect[2] <= z < rect[3]
        site = build.found(g, "MILL", rect)
        assert build.rise(g, site, build.BUILD_TIMES["MILL"])        # all blocks of the mill
        time.sleep(5)
        x, y, z = g.pos(m)
        assert not (rect[0] <= x < rect[1] and rect[2] <= z < rect[3]), (x, z, rect)
        assert (health(game, "m") or 0) > 0
        x, y, z = g.pos(c)
        assert not (rect[0] <= x < rect[1] and rect[2] <= z < rect[3]), (x, z, rect)
        assert "has the following" in game.command(f"data get entity {c} Passengers")   # the rider stays on the horse
