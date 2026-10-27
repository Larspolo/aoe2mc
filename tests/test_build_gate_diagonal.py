"""game/build.py: a gate on a diagonal wall line (#1655). Fake server, no Minecraft."""
import math
import shutil
import time
import types

import pytest
from test_build_gates import blocks
from test_build_site import site_map
from test_plugin import pos

from game import build, run

SIDE = {"west": (1, 0), "east": (-1, 0), "north": (0, 1), "south": (0, -1)}    # the side of a closed door panel


def test_a_gate_goes_on_3_tiles_of_a_diagonal_wall_line_in_both_directions():
    for a, b, way, tiles, free in (((6, 6), (10, 10), "diag+", [(7, 7), (8, 8), (9, 9)], (7, 9)),
                                   ((6, 10), (10, 6), "diag-", [(7, 9), (8, 8), (9, 7)], (7, 7))):
        server, g = site_map(wood=200)
        build.wall(g, "Steve", "PALISADE_WALL", a)
        build.wall(g, "Steve", "PALISADE_WALL", b)
        assert build.gate_rect(g, (8, 8)) == (7, 10, 7, 10)                       # 3 x 3 tiles, as in AoE2
        site = build.gate(g, "Steve", "PALISADE_GATE", (8, 8))
        assert site["footprint"] == (7, 10, 7, 10) and site["way"] == way and site["tiles"] == tiles
        assert sorted(s["footprint"][::2] for s in g.sites if s is not site) == sorted([a, b])   # the ends stay
        assert {tiles[0], tiles[2]} <= blocks(site) and free not in blocks(site)   # the design on the diagonal, open in the middle
        assert g.map.free(*free) and not g.map.free(8, 8)
        assert build.rise(g, site, math.inf)
        assert g.map.free(*free) and not g.map.free(*tiles[0])                  # beside the gate: still free
        assert "fill 8 64 8 8 66 8 minecraft:iron_bars" in server.log             # the portcullis (#1656)


def test_a_bent_line_takes_no_diagonal_gate():
    server, g = site_map(wood=200)
    for a, b in (((6, 6), (7, 7)), ((8, 7), (8, 7))):                          # (6, 6), (7, 7), then a step along x
        build.wall(g, "Steve", "PALISADE_WALL", a)
        build.wall(g, "Steve", "PALISADE_WALL", b)
    assert build.gate(g, "Steve", "PALISADE_GATE", (7, 7)) is None
    assert any("or on 3 diagonal tiles" in c for c in server.log)


def test_the_doors_of_a_diagonal_gate_close_the_passage():
    """The passage of buildings.diagonal_gate (T = 4): the cells with |x - z| <= T / 2 and T <= (x + z) / 2 < 2 T. A
    unit crosses it from x > z to x < z; the closed panels of the doors (3/16 of a block) must cut each way."""
    T = 4
    for way in ("diag+", "diag-"):
        doors = build.diagonal_doors({"footprint": (0, 3 * T, 0, 3 * T), "way": way}, T)
        flip = (lambda x, z: (x, 3 * T - 1 - z)) if way == "diag-" else (lambda x, z: (x, z))
        opening = {flip(x, z) for x in range(3 * T) for z in range(3 * T) if abs(x - z) <= T // 2 and T <= (x + z) / 2 < 2 * T}
        panels = {(x, z): SIDE[f] for x, z, f, _ in doors}
        assert set(panels) <= opening | {flip(T, T - 1)}

        def cut(a, b):
            d = (b[0] - a[0], b[1] - a[1])
            return panels.get(a) == d or panels.get(b) == (-d[0], -d[1])

        side = {c for c in opening if flip(*c)[0] > flip(*c)[1] and c not in panels}    # x > z (before the mirror)
        seen, todo = set(side), list(side)
        while todo:
            x, z = todo.pop()
            for n in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
                if n in opening | set(panels) and n not in seen and not cut((x, z), n):
                    seen.add(n)
                    todo.append(n)
        assert not any(flip(*c)[0] < flip(*c)[1] for c in seen - set(panels)), way


@pytest.mark.mc
def test_a_diagonal_gate_opens_for_an_own_unit_and_not_for_an_enemy(tiny_world, tmp_path):
    """Paper: the portcullis on the cells of diagonal_doors on the passage of a diagonal band of wall (T = 4) lets an
    own unit through and keeps an enemy on its side (#1655, #1656)."""
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    T, x0, y, z0, n = 4, 1, 200, 1, 30                                 # a floor in the air, inside the world border
    ox, oz = x0 + 6, z0 + 6                                            # the north-west corner of the gate footprint
    site = {"name": "PALISADE_GATE", "player": 1, "footprint": (ox, ox + 3 * T, oz, oz + 3 * T), "way": "diag+"}
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + n + 2} {z0 + n + 2}")
        game.command(f"fill {x0} {y - 1} {z0} {x0 + n} {y - 1} {z0 + n} stone_bricks")
        for x in range(x0, x0 + n + 1):                                # the band x - z = const. from edge to edge
            for z in range(z0, z0 + n + 1):
                u, v = (x - ox + z - oz) / 2, x - ox - (z - oz)
                if abs(v) <= T // 2:                                   # the passage: 3 blocks high (diagonal_gate)
                    game.command(f"fill {x} {y + 3 * (T <= u < 2 * T)} {z} {x} {y + 3} {z} stone")
        game.command("time set midnight")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        g = types.SimpleNamespace(command=game.command, paper=True, map=types.SimpleNamespace(T=T, y=lambda x, z: y))
        build.portcullis(g, site)
        assert "passed" in game.command(f"execute if block {ox + 6} {y} {oz + 6} minecraft:iron_bars")
        units = {"own": ((12, 0), (0, 12), "p1"), "enemy": ((20, 8), (8, 20), "p2")}   # 12 blocks off the band (v)

        def side(tag):                                                 # x - z of the unit, local
            p = pos(game, tag)
            return p and p[0] - ox - (p[2] - oz)
        for tag, ((ax, az), (bx, bz), team) in units.items():         # one after the other: an open gate lets all in
            game.command(f'summon zombie {ox + ax + 0.5} {y} {oz + az + 0.5} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join {team} @e[tag={tag}]")
            assert game.command(f"aoe moveto @e[tag={tag}] {ox + bx + 0.5} {y} {oz + bz + 0.5}").strip() == "Moved 1 units"
            end = time.time() + 30
            while time.time() < end and not (side(tag) is not None and side(tag) < -4):
                time.sleep(0.2)
            if tag == "own":
                assert side("own") < -4, pos(game, "own")              # through the open gate
                end = time.time() + 10                                 # closed again: no own unit near
                while time.time() < end and "passed" not in game.command(f"execute if block {ox + 6} {y} {oz + 6} "
                                                                         "minecraft:iron_bars"):
                    time.sleep(0.5)
                assert time.time() < end, pos(game, "own")
        assert side("enemy") > 2, pos(game, "enemy")                   # the enemy stays on its side
