#!/usr/bin/env python3
"""
Isometric 3D image of a building design or of an area of a written world. To look at designs without Minecraft.

Usage:
    python3 tools/render.py building CASTLE --arch western OUT.png       # [--tile-size 4] [--view se] [--scale 8]
    python3 tools/render.py sheet HOUSE OUT.png                           # all architecture sets, 3 variants each
    python3 tools/render.py building MILL OUT.png --cut 2                 # the inside: no blocks above floor + 2
    python3 tools/render.py world WORLD X0 Z0 X1 Z1 OUT.png               # [--view se] [--scale 8]

The default view is from the south-east (the AoE2 camera side, the front of a building). Top faces are
lighter, side faces darker. Colors come from the textures (tools/fetch_colors.py). Barriers and air are invisible. Transparent blocks (glass, leaves ...) are lighter.

    import render
    render.render(xs, ys, zs, states, "out.png")        # states: one state name per block
"""
import argparse
import functools
import json
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.dirname(os.path.abspath(__file__))]

import aoe2mc  # noqa: E402

INVISIBLE = ("air", "cave_air", "void_air", "barrier", "structure_void", "light")
TRANSPARENT = ("glass", "leaves", "water", "ice", "iron_bars", "chain", "fence", "pane", "torch", "lantern",
               "short_grass", "tall_grass", "fern", "flower", "bush", "sapling", "seagrass", "carpet", "banner", "button", "rail")
SHADE = np.array([1.08, 0.82, 0.62])            # top, south (left) and east (right) faces, for the south-east view
ROT = {"se": lambda x, z: (x, z), "sw": lambda x, z: (z, -x), "ne": lambda x, z: (-z, x), "nw": lambda x, z: (-x, -z)}


def base_name(state):
    return state.split(":")[-1].split("[")[0]


def sprite(s):
    """Pixel offsets (du, dv) of one block and their face (0 top, 1 south, 2 east), plus an edge flag."""
    t = (np.arange(4 * s) + 0.5) / (4 * s)
    a, b = (g.ravel() for g in np.meshgrid(t, t))
    one = np.ones_like(a)
    faces = {}
    for f, (x, y, z) in enumerate([(a, one, b), (a, b, one), (one, b, a)]):    # top, south, east
        u, v = (x - z) * s, (x + z) * s / 2 - y * s
        for du, dv in set(zip(np.floor(u).astype(int), np.floor(v).astype(int))):
            faces.setdefault((du, dv), f)
    du, dv = np.array(list(faces)).T
    f = np.array(list(faces.values()))
    edge = np.array([any(faces.get((x + dx, y + dy), -1) != g for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                     for x, y, g in zip(du, dv, f)])
    return du, dv, f, edge


@functools.lru_cache(maxsize=None)
def texture_colors(version="1.21.1"):
    """{block name: (top RGB, side RGB)} from the textures (tools/fetch_colors.py), or {} without the file."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcdata", f"colors-{version}.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)["blocks"]


def colors(states):
    """RGB per state and face (top, side), and a transparent flag. Stairs and slabs without texture colors (new in 26.3,
    such as white_wool_stairs) take the colors of their full block, else block_color()."""
    tex = texture_colors()
    rgb = np.array([tex.get(base_name(s)) or tex.get(base_name(s).removesuffix("_stairs").removesuffix("_slab")) or [aoe2mc.block_color(s if ":" in s else "minecraft:" + s)] * 2
                    for s in states], float)
    clear = np.array([any(k in base_name(s) for k in TRANSPARENT) for s in states])
    rgb[clear] = rgb[clear] * 0.6 + 255 * 0.4
    return rgb, clear


def render(xs, ys, zs, states, out, **kw):
    """Draw blocks at (xs, ys, zs) with state names `states` as an isometric PNG. Return the image size."""
    img = draw(xs, ys, zs, states, **kw)
    img.save(out)
    return img.size


def draw(xs, ys, zs, states, view="se", scale=8, background=(255, 255, 255, 0)):
    """The isometric image (PIL, RGBA) of blocks at (xs, ys, zs) with state names `states`."""
    names = sorted(set(states))
    idx = {n: i for i, n in enumerate(names)}
    sid = np.array([idx[s] for s in states], np.int32)
    xs, zs = ROT[view](np.asarray(xs, np.int64), np.asarray(zs, np.int64))
    ys = np.asarray(ys, np.int64)
    show = ~np.array([base_name(n) in INVISIBLE for n in names])[sid]
    xs, ys, zs, sid = xs[show], ys[show], zs[show], sid[show]
    if not len(xs):
        return Image.new("RGBA", (1, 1), background)
    rgb, clear = colors(names)
    # Hide blocks that have opaque blocks on all three visible sides
    lo = np.array([xs.min(), ys.min(), zs.min()])
    p = np.stack([xs, ys, zs], 1) - lo
    solid = np.zeros(tuple(p.max(0) + 2), bool)
    solid[tuple(p[~clear[sid]].T)] = True
    seen = ~(solid[p[:, 0] + 1, p[:, 1], p[:, 2]] & solid[p[:, 0], p[:, 1] + 1, p[:, 2]] & solid[p[:, 0], p[:, 1], p[:, 2] + 1])
    xs, ys, zs, sid = xs[seen], ys[seen], zs[seen], sid[seen]

    du, dv, face, edge = sprite(scale)
    u = ((xs - zs) * scale)[:, None] + du[None]
    v = ((xs + zs) * scale // 2 - ys * scale)[:, None] + dv[None]
    depth = np.broadcast_to((xs + ys + zs)[:, None], u.shape)
    u, v, depth = u.ravel(), v.ravel(), depth.ravel()
    u, v = u - u.min(), v - v.min()
    W, H = int(u.max()) + 1, int(v.max()) + 1
    pix = v * W + u
    order = np.lexsort((-depth, pix))                       # per pixel: the nearest block first
    pix = pix[order]
    first = np.r_[True, pix[1:] != pix[:-1]]
    k = order[first]
    blk, f = k // len(du), k % len(du)
    col = rgb[sid[blk], np.minimum(face[f], 1)] * SHADE[face[f]][:, None] * np.where(edge[f], 0.85, 1.0)[:, None]
    img = np.zeros((H * W, 4), np.uint8)
    img[:] = background
    img[pix[first], :3] = np.clip(col, 0, 255).astype(np.uint8)
    img[pix[first], 3] = 255
    return Image.fromarray(img.reshape(H, W, 4), "RGBA")


def building_blocks(name, arch, T=4, variant=0, cut=None):
    """Blocks of one building design on flat grass: (xs, ys, zs, states).
    The design seeds its random numbers from the position, so another variant number gives another variant.
    cut: remove the blocks higher than cut above the ground (a view of the inside)."""
    import buildings
    size = 16
    cols = aoe2mc.Columns(size, np.zeros((size, size), np.int16), np.zeros((size, size), np.float32),
                          {0: "GRASS_1"}, T, 3, np.random.default_rng(1))
    E = aoe2mc.Edits(cols)
    players = {1: {"color": "blue", "arch": arch, "civ": "RENDER"}}
    o = dict(kind="B", name=name, player=1, x=size / 2 + variant % 3, y=size / 2 + variant // 3, rotation=0.0, hero=False, garrisoned=False)
    walls, gates = buildings.plan_walls([o])
    buildings.place_building(E, cols, aoe2mc.B, o, players, walls, gates)
    if not E.parts:
        raise SystemExit(f"{name}: no blocks (unknown building name?)")
    x, y, z, ids, _ = (np.concatenate(p) for p in zip(*E.parts))
    last = {}                                               # later edits replace earlier ones, as in build_chunk
    for p in zip(x.tolist(), y.tolist(), z.tolist(), ids.tolist()):
        last[p[:3]] = p[3]
    gx0, gx1 = min(k[0] for k in last) - 2, max(k[0] for k in last) + 3
    gz0, gz1 = min(k[2] for k in last) - 2, max(k[2] for k in last) + 3
    for gx in range(gx0, gx1):                              # the ground, so that the building stands on something
        for gz in range(gz0, gz1):
            last.setdefault((gx, cols.surface(gx, gz) - 1, gz), aoe2mc.B("grass_block[snowy=false]"))
    if cut is not None:
        top = cols.surface(gx0, gz0) - 1 + cut
        last = {k: v for k, v in last.items() if k[1] <= top}
    pos = np.array(list(last), np.int64)
    return pos[:, 0], pos[:, 1], pos[:, 2], [aoe2mc.B.states[i] for i in last.values()]


def world_blocks(path, x0, z0, x1, z1, y0=aoe2mc.MIN_Y):
    """Blocks of a written world in x0 <= x < x1, z0 <= z < z1 and y >= y0: (xs, ys, zs, states)."""
    import world_reader
    w = world_reader.World(path)
    out = [[], [], [], []]
    for cx in range(x0 >> 4, ((x1 - 1) >> 4) + 1):
        for cz in range(z0 >> 4, ((z1 - 1) >> 4) + 1):
            c = w.chunk(cx, cz)
            for s in c["sections"] if c is not None else []:
                names, idx = w.section_states(s)
                if len(names) == 1 and base_name(names[0]) == "air" or int(s["Y"]) * 16 + 15 < y0:
                    continue
                idx = np.array(idx).reshape(16, 16, 16)         # (y, z, x)
                ly, lz, lx = np.nonzero(np.ones_like(idx, bool))
                gx, gz, gy = cx * 16 + lx, cz * 16 + lz, int(s["Y"]) * 16 + ly
                ok = (gx >= x0) & (gx < x1) & (gz >= z0) & (gz < z1) & (gy >= y0)
                out[0].append(gx[ok]), out[1].append(gy[ok]), out[2].append(gz[ok])
                out[3] += [names[i] for i in idx[ly[ok], lz[ok], lx[ok]]]
    if not out[0]:
        return np.zeros(0, int), np.zeros(0, int), np.zeros(0, int), []
    return np.concatenate(out[0]), np.concatenate(out[1]), np.concatenate(out[2]), out[3]


def sheet(name, out, view="se", scale=6, variants=3, T=4, cut=None):
    """One image with the design in all architecture sets (rows) and some variants (columns)."""
    from PIL import ImageDraw

    import buildings
    rows = [(arch, [draw(*building_blocks(name, arch, T, v, cut), view=view, scale=scale) for v in range(variants)])
            for arch in sorted(buildings.ARCH)]
    cw = max(i.width for _, r in rows for i in r) + 8
    ch = max(i.height for _, r in rows for i in r) + 16
    img = Image.new("RGB", (cw * variants, ch * len(rows)), (255, 255, 255))
    d = ImageDraw.Draw(img)
    for j, (arch, row) in enumerate(rows):
        d.text((4, j * ch + 2), arch, fill=(0, 0, 0))
        for i, im in enumerate(row):
            img.paste(im, (i * cw, j * ch + 14), im)
    img.save(out)
    return img.size


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    b = sub.add_parser("building", help="one building design on flat grass")
    b.add_argument("name", help="AoE2 building name, for example CASTLE or HOUSE")
    b.add_argument("--arch", default="western", help="architecture set (see buildings.ARCH)")
    b.add_argument("--tile-size", type=int, default=4)
    h = sub.add_parser("sheet", help="one building in all architecture sets and some variants")
    h.add_argument("name")
    h.add_argument("--variants", type=int, default=3)
    h.add_argument("--tile-size", type=int, default=4)
    for p in (b, h):
        p.add_argument("--cut", type=int, help="remove the blocks higher than CUT above the ground (the inside)")
    w = sub.add_parser("world", help="an area of a written world")
    w.add_argument("world")
    for k in ("x0", "z0", "x1", "z1"):
        w.add_argument(k, type=int)
    w.add_argument("--y0", type=int, default=aoe2mc.WATER_Y - 12, help="lowest Y to draw (default: %(default)s)")
    for p in (b, h, w):
        p.add_argument("out")
        p.add_argument("--view", choices=sorted(ROT), default="se")
        p.add_argument("--scale", type=int, default=6 if p is h else 8, help="pixels per half block edge (even number)")
    a = ap.parse_args()
    if a.scale < 2 or a.scale % 2:
        ap.error("--scale must be an even number >= 2")
    if a.mode == "sheet":
        W, H = sheet(a.name.upper(), a.out, a.view, a.scale, a.variants, a.tile_size, a.cut)
        print(f"Wrote {a.out}: {W}x{H} pixels")
        return
    if a.mode == "building":
        blocks = building_blocks(a.name.upper(), a.arch, a.tile_size, cut=a.cut)
    else:
        blocks = world_blocks(a.world, min(a.x0, a.x1), min(a.z0, a.z1), max(a.x0, a.x1), max(a.z0, a.z1), a.y0)
    W, H = render(*blocks, a.out, view=a.view, scale=a.scale)
    print(f"Wrote {a.out}: {W}x{H} pixels, {len(blocks[3])} blocks")


if __name__ == "__main__":
    main()
