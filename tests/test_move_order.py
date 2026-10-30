"""game/gather.py: a right click on free ground with selected units moves them there, as the move order of AoE2
(#1368): each unit to its own free cell near the click (2 or more military units in the line formation, #3414),
military units with `aoe moveto` of the plugin at their AoE2 speed, villagers stop their work and walk there."""
import math
import re

import pytest
from test_gather import FakeServer, grid

from game import ai, gather, replay, train

STEVE = {"Pos": (8.5, 64.0, 12.5), "Rotation": (-90.0, 30.0)}  # looks east and down at the ground near x = 10


def setup(militia=3, villagers=2):
    """A flat 24 × 24 map (tile size 1) with own militia "m0" ... at z = 18 and villagers "v0" ... at z = 20."""
    objects = [{"kind": "unit", "name": "MILITIA", "player": 1, "uuid": f"m{k}", "tile": [4.5 + k, 18.5]}
               for k in range(militia)]
    objects += [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": f"v{k}", "tile": [4.5 + k, 20.5]}
                for k in range(villagers)]
    ents = {o["uuid"]: {"Pos": (o["tile"][0], 64.0, o["tile"][1])} for o in objects} | {"Steve": STEVE}
    server = FakeServer(ents)
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()
    g.paper = True
    return server, g


def moves(server):
    """{uuid: (x, z)} of the `aoe moveto` commands in the log."""
    return {m[1]: (float(m[2]), float(m[4])) for c in server.log if (m := re.fullmatch(r"aoe moveto (\S+) (\S+) (\S+) (\S+)", c))}


def test_a_click_on_the_ground_sends_each_soldier_to_its_own_free_cell_near_it():
    server, g = setup()
    cell = g.map.pick_ground(*g.look("Steve"))
    g.choose({"m0", "m1", "m2"}, "m0")
    server.log.clear()
    g.click("Steve")
    to = moves(server)
    assert set(to) == {"m0", "m1", "m2"} and len(set(to.values())) == 3          # different cells
    assert (cell[0] + 0.5, cell[1] + 0.5) in to.values()                         # the first row on the clicked cell
    assert all(math.dist(p, (cell[0] + 0.5, cell[1] + 0.5)) <= 2 * replay.FORMATION for p in to.values())   # #3414
    speed = ai.speed_command("m0", "MILITIA", g.map.T, gather.NORMAL * train.speed(g, "MILITIA"))
    assert speed in server.log
    assert any(c.startswith("particle ") for c in server.log)                     # the order marker


def test_selected_villagers_stop_their_work_and_walk_there():
    server, g = setup(militia=0)
    v = g.villagers["v0"]
    v.tree, v.state = (12, 12), "chop"
    g.choose({"v0", "v1"}, "v0")
    out = g.walk_to("Steve", (10, 12))
    assert out == {"v0": (10, 12), "v1": (9, 12)}                    # the nearest free cells, (x, z) order
    assert v.tree is None and v.state == "to_rally" and g.villagers["v1"].state == "to_rally"
    assert {u: g.villagers[u].goal for u in out} == out


def test_the_action_bar_says_move_only_with_a_selection():
    server, g = setup()
    assert g.says("ground", (10, 12)) == "Ground"
    g.choose({"m0"}, "m0")
    assert g.says("ground", (10, 12)) == "Ground · Right click: move"


def test_no_move_without_a_selection_or_onto_a_blocked_cell():
    server, g = setup()
    g.click("Steve")
    assert not moves(server)
    g.choose({"m0"}, "m0")
    g.map.blocked |= {g.map.pick_ground(*g.look("Steve"))}
    g.click("Steve")
    assert not moves(server)


@pytest.mark.mc
def test_a_selected_militia_walks_to_the_clicked_cell_on_a_server(tmp_path):
    """A selected militia walks 8 tiles to the cell of a move order on a Paper server (#1368)."""
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import contextlib
    import io
    import json
    import time

    import scenarios
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
    from game import run
    scn = scenarios.new_scenario(24)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, UnitInfo.MILITIA.ID, x=6.5, y=12.5)
    src = str(tmp_path / "m.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        g = gather.Gather(game, data, tick=0.25).setup()
        u, = g.soldiers
        x, _, z = g.pos(u)
        cell = (math.floor(x) + 8 * g.map.T, math.floor(z))
        assert g.map.free(*cell)
        g.choose({u}, u)
        assert g.walk_to("nobody", cell) == {u: cell}
        end = time.time() + 40
        while math.dist((g.pos(u)[0], g.pos(u)[2]), (cell[0] + 0.5, cell[1] + 0.5)) > 1.5:
            assert time.time() < end, (g.pos(u), cell)
            time.sleep(0.5)
