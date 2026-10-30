"""game/gather.py: a right click selects an own herdable animal, and a right click on the ground walks it there with
`aoe moveto`, as in AoE2 (#1791). With villagers selected, a click on it stays the hunt order (#1058)."""
import re

import pytest
from test_gather import FakeServer, grid

from game import gather

LOOK = {"Pos": (8.5, 63.38, 6.5), "Rotation": (180.0, 0.0)}           # 4 blocks south of (8.5, 2.5), looks north


def setup(owner=1):
    """A flat 24 × 24 map (tile size 1): a sheep "s" of owner at (8.5, 2.5), an own goat "g" at (12.5, 2.5), an own
    villager "v" at (4.5, 20.5) and an own militia "m" at (6.5, 20.5)."""
    objects = [{"kind": "unit", "name": "SHEEP", "player": owner, "uuid": "s", "tile": [8.5, 2.5]},
               {"kind": "unit", "name": "GOAT", "player": 1, "uuid": "g", "tile": [12.5, 2.5]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [4.5, 20.5]},
               {"kind": "unit", "name": "MILITIA", "player": 1, "uuid": "m", "tile": [6.5, 20.5]}]
    ents = {o["uuid"]: {"Pos": (o["tile"][0], 64.0, o["tile"][1])} for o in objects} | {"Steve": dict(LOOK)}
    server = FakeServer(ents)
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()
    g.paper = True
    return server, g


def moves(server):
    return {m[1]: (float(m[2]), float(m[4])) for c in server.log if (m := re.fullmatch(r"aoe moveto (\S+) (\S+) (\S+) (\S+)", c))}


def test_a_click_on_an_own_sheep_selects_it():
    server, g = setup()
    kind, key, _ = g.target(*g.look("Steve"), g.positions(sorted(g.pickable())))
    assert (kind, key) == ("unit", "s") and g.says(kind, key) == "Sheep · Right click: select"
    g.click("Steve")
    assert g.selected == {"s"}
    assert "data merge entity s {Glowing:1b}" in server.log and f"tag s add {gather.SELECT}" in server.log
    assert any(c.startswith("bossbar set ") and '"Sheep"' in c for c in server.log)   # the boss bar names it


def test_selected_herdables_walk_to_the_clicked_ground():
    server, g = setup()
    g.choose({"s", "g"}, "s")
    server.log.clear()
    out = g.walk_to("Steve", (10, 12))
    assert set(out) == {"s", "g"} and len(set(out.values())) == 2
    assert set(moves(server)) == {"s", "g"}
    assert any(c.startswith("attribute s minecraft:movement_speed") for c in server.log)


def test_with_a_villager_selected_a_click_on_an_own_sheep_hunts_it():
    server, g = setup()
    g.select("v")
    kind, key, _ = g.target(*g.look("Steve"), g.positions(sorted(g.pickable())))
    assert (kind, key) == ("prey", "s")
    g.click("Steve")
    assert g.villagers["v"].prey == "s" and g.selected == {"v"}


def test_an_enemy_or_gaia_sheep_cannot_be_selected():
    for owner in (0, 2):
        server, g = setup(owner)
        assert "s" not in g.pickable() and "s" not in g.herd()
        g.click("Steve")
        assert "s" not in g.selected


def test_a_selection_box_takes_villagers_and_soldiers_before_herdables():
    server, g = setup()
    g.box("Steve", (0, 0))
    g.box("Steve", (23, 23))
    assert g.selected == {"m"}                                         # soldiers win
    g.box("Steve", (0, 0))
    g.box("Steve", (23, 10))
    assert g.selected == {"s", "g"}                                    # only herdables in the box


def test_a_dead_herdable_leaves_the_flock():
    server, g = setup()
    g.prey.pop("s")
    assert g.herd() == {"g"} and "s" not in g.pickable()


@pytest.mark.mc
def test_a_selected_own_sheep_walks_to_the_clicked_cell_on_a_server(tmp_path):
    """An own sheep that a click selects walks 8 tiles to the cell of a move order on a Paper server."""
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import contextlib
    import io
    import json
    import math
    import time

    import scenarios
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
    from game import run
    scn = scenarios.new_scenario(24)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, UnitInfo.SHEEP.ID, x=6.5, y=12.5)
    src = str(tmp_path / "s.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        g = gather.Gather(game, data, tick=0.25).setup()
        u, = g.herd()
        x, _, z = g.pos(u)
        cell = (math.floor(x) + 8 * g.map.T, math.floor(z))
        assert g.map.free(*cell)
        g.select(u)
        assert g.selected == {u} and g.walk_to("nobody", cell) == {u: cell}
        end = time.time() + 60
        while math.dist((g.pos(u)[0], g.pos(u)[2]), (cell[0] + 0.5, cell[1] + 0.5)) > 1.5:
            assert time.time() < end, (g.pos(u), cell)
            time.sleep(0.5)
