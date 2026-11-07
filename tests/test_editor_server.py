"""A map made only with the editor on a real server (#6008, epic #5998): paint, water, raise, dig, place, remove, the
players menu and save; the saved scenario has each part, and aoe2mc.convert converts it again."""
import contextlib
import io
import json
import os
import shutil
import sys

import pytest
from test_mc_check import mojang_reachable

import aoe2mc
from tools import scenarios

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
RESOURCES = ("TREE_OAK_FOREST", "GOLD_MINE", "STONE_MINE", "FORAGE_BUSH", "SHEEP")   # trees, gold, stone, berries, animals


def free_tiles(s, data, k):
    """k free, flat tiles far apart, not under an object: (tile x, tile y, the Y of their top block)."""
    import export
    T, skip, out = s.map.T, export.covered(data), []
    for ty in range(1, s.map.n // T - 1, 2):
        for tx in range(1, s.map.n // T - 1, 2):
            cells = [(x, z) for x in range(tx * T - 1, tx * T + T + 1) for z in range(ty * T - 1, ty * T + T + 1)]
            ys = {s.map.y(*c) for c in cells}
            if (tx, ty) not in skip and len(ys) == 1 and None not in ys and all(s.map.free(*c) for c in cells):
                out.append((tx, ty, ys.pop() - 1))
    assert len(out) >= k, out
    return sorted(out, key=lambda t: -t[2])[:k]                       # the high tiles first: one of them is dug


@pytest.mark.mc
def test_a_map_made_with_the_editor_saves_and_converts(tmp_path):
    from test_paper import paper_reachable
    if not mojang_reachable() or not paper_reachable():
        pytest.skip("Mojang or Paper is not available")
    import editor
    import export
    from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
    from test_editor_palette import eye_over

    from game import run
    world, out = str(tmp_path / "W"), str(tmp_path / "OUT.aoe2scenario")
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(scenarios.tiny(str(tmp_path / "tiny.aoe2scenario")), world)
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    T, H = data["tile_size"], data.get("level_height", 3)
    elevation = [[int(v) for v in r.split()] for r in data["elevation"]]
    tops, of, _ = export.terrain_tops()
    with run.Game(world) as game:
        game.forceload()
        s = editor.State(game, data)
        dig, paint, water, high, *spots = free_tiles(s, data, 4 + 10)
        assert elevation[dig[1]][dig[0]] >= 1
        box = lambda t, y0, y1, b: game.command(                     # noqa: E731
            f"fill {t[0] * T} {y0} {t[1] * T} {t[0] * T + T - 1} {y1} {t[1] * T + T - 1} {b}")
        start = lambda t: of[int(data["terrain"][t[1]].split()[t[0]])]   # noqa: E731
        new = next(b for b in tops if b not in ("farmland", "sand", "gravel") and not export.same(b, start(paint)))
        box(paint, paint[2], paint[2], new)                            # 1. paint a tile, water on a tile
        box(water, water[2], water[2], "gravel")
        box(water, water[2] + 1, water[2] + 1, "water")
        box(high, high[2] + 1, high[2] + H, start(high))               # 2. raise a tile, dig a tile
        box(dig, dig[2] - H + 1, dig[2], "air")
        unit = next(n for n in dict(editor.tabs())["units"] if editor.kind(n) == "U")
        house = dict(editor.tabs())["buildings"][0]
        want = [(unit, 1), (house, 1), (unit, 2), (house, 2), (unit, 0)] + [(r, 0) for r in RESOURCES]
        placed = []
        for (name, p), (tx, ty, _) in zip(want, spots):                # 3. place for player 1, 2 and Gaia
            s.player = p
            o = editor.place(s, "p", name, *eye_over(s, (tx * T + T // 2, ty * T + T // 2)))
            assert o is not None, name
            placed.append((export.unit_id(name), o["player"], o["tile"]))
        assert [p for _, p, _ in placed] == [p for _, p in want]
        i, gone = next((i, o) for i, o in enumerate(data["objects"]) if o["kind"] == "building" and "footprint" in o)
        x0, z0, x1, z1 = gone["footprint"]
        assert editor.remove(s, "p", *eye_over(s, ((x0 + x1) // 2, (z0 + z1) // 2))) is not None   # 4. remove
        civ = {}
        for p in (1, 2):                                               # 5. civilization, resources and age
            editor.players_menu(s, "p")
            s.menus["p"]("p", p, False)
            s.menus["p"]("p", editor.CIV, False)
            s.menus["p"]("p", editor.RES + p, False)                   # wood +100 (p1), gold +100 (p2)
            s.menus["p"]("p", editor.AGE + p, False)
            civ[p] = s.data["players"][str(p)]["civ"]
        with contextlib.redirect_stdout(io.StringIO()):
            editor.save(game, out, s)                                  # 6. save
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(out)
    tiles = {(t.x, t.y): t for t in scn.map_manager.terrain}
    assert tiles[paint[:2]].terrain_id == tops[new]
    assert tiles[water[:2]].terrain_id == tops["gravel"]
    assert tiles[high[:2]].elevation == elevation[high[1]][high[0]] + 1
    assert tiles[dig[:2]].elevation == elevation[dig[1]][dig[0]] - 1
    units = [(u.unit_const, p, u.x, u.y) for p in range(9) for u in scn.unit_manager.units[p]]
    for uid, p, (x, y) in placed:
        assert any(c == uid and q == p and abs(ux - x) <= 1 and abs(uy - y) <= 1 for c, q, ux, uy in units), (uid, p, x, y)
    start = sum(1 for o in data["objects"] if (o.get("id"), o.get("player")) == (gone["id"], gone["player"]))
    mine = sum(1 for uid, p, _ in placed if (uid, p) == (gone["id"], gone["player"]))
    assert sum(1 for c, q, _, _ in units if (c, q) == (gone["id"], gone["player"])) == start - 1 + mine
    for p in (1, 2):
        pl = scn.player_manager.players[p]
        assert pl.civilization.name == civ[p] or civ[p] not in export.Civilization.__members__
        assert (pl.wood if p == 1 else pl.gold) == 100
        assert pl.starting_age == export.AGES[p]
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(out, str(tmp_path / "W2"))                     # converts again with no error
    assert os.path.exists(tmp_path / "W2" / "level.dat")
    shutil.rmtree(tmp_path / "W2")
