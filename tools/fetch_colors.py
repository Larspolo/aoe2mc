#!/usr/bin/env python3
"""
Make a block color file for one Java version from the textures in the Minecraft client jar (Mojang hosts).

Usage:
    python3 tools/fetch_colors.py 1.21.1 [--jar CLIENT.jar]

Writes tools/mcdata/colors-<version>.json with {block name: [[r, g, b] of the top, [r, g, b] of the side]}.
Each color is the average of the visible pixels of the texture that the block model uses. Biome-tinted
textures (grass, leaves, water, vines) get a fixed tint, as in the plains biome. tools/render.py reads this file.
"""
import argparse
import io
import json
import os
import tempfile
import urllib.request
import zipfile

import numpy as np
from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcdata")
MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
TOP = ("top", "end", "up", "all", "texture", "cross", "plant", "crop", "flower", "pattern", "particle")
SIDE = ("side", "front", "north", "all", "texture", "cross", "plant", "crop", "flower", "pattern", "particle")
GRASS, FOLIAGE = (145, 189, 89), (119, 171, 47)
TINT = {"grass_block_top": GRASS, "short_grass": GRASS, "tall_grass_top": GRASS, "tall_grass_bottom": GRASS,
        "fern": GRASS, "large_fern_top": GRASS, "large_fern_bottom": GRASS, "sugar_cane": GRASS,
        "potted_fern": GRASS, "vine": FOLIAGE, "oak_leaves": FOLIAGE, "jungle_leaves": FOLIAGE,
        "acacia_leaves": FOLIAGE, "dark_oak_leaves": FOLIAGE, "mangrove_leaves": (146, 198, 72),
        "spruce_leaves": (97, 153, 97), "birch_leaves": (128, 167, 85), "lily_pad": (32, 128, 48),
        "water_still": (63, 118, 228), "water_flow": (63, 118, 228)}


def jar(version, path=None):
    if path:
        return zipfile.ZipFile(path)
    get = lambda url: urllib.request.urlopen(url, timeout=120).read()
    v = next(v for v in json.loads(get(MANIFEST))["versions"] if v["id"] == version)
    url = json.loads(get(v["url"]))["downloads"]["client"]["url"]
    tmp = tempfile.TemporaryFile()
    tmp.write(get(url))
    return zipfile.ZipFile(tmp)


def first_model(state):
    """The model name of the first variant (or of the first multipart part) of a blockstate file."""
    if "variants" in state:
        v = next(iter(state["variants"].values()))
    else:
        v = state["multipart"][0]["apply"]
    return (v[0] if isinstance(v, list) else v)["model"]


def textures(z, model, seen=()):
    """All texture variables of a model and its parents, resolved to texture names."""
    name = model.split(":")[-1]
    try:
        m = json.loads(z.read(f"assets/minecraft/models/{name}.json"))
    except KeyError:
        return {}
    tex = textures(z, m["parent"], seen + (name,)) if "parent" in m and name not in seen else {}
    tex.update(m.get("textures", {}))
    for _ in range(5):                                      # "#side" refers to another variable
        tex = {k: tex.get(v[1:], v) if isinstance(v, str) and v.startswith("#") else v for k, v in tex.items()}
    return {k: v for k, v in tex.items() if isinstance(v, str) and not v.startswith("#")}


def average(z, texture):
    name = texture.split(":")[-1].split("/")[-1]
    try:
        img = Image.open(io.BytesIO(z.read(f"assets/minecraft/textures/{texture.split(':')[-1]}.png"))).convert("RGBA")
    except KeyError:
        return None
    a = np.asarray(img, float)[:img.width]                  # animated textures: the first frame only
    vis = a[..., 3] > 0
    if not vis.any():
        return None
    rgb = (a[..., :3][vis] * a[..., 3][vis, None]).sum(0) / a[..., 3][vis].sum()
    if name in TINT:
        rgb = rgb * np.array(TINT[name]) / 255
    return [int(round(c)) for c in rgb]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip())
    ap.add_argument("version", nargs="?", default="1.21.1")
    ap.add_argument("--jar", help="a client jar that you downloaded before")
    a = ap.parse_args()
    z = jar(a.version, a.jar)
    colors = {}
    for f in sorted(z.namelist()):
        if not (f.startswith("assets/minecraft/blockstates/") and f.endswith(".json")):
            continue
        block = f.rsplit("/", 1)[1][:-5]
        tex = textures(z, first_model(json.loads(z.read(f))))
        pick = lambda keys: next((tex[k] for k in keys if k in tex), next(iter(tex.values()), None))
        top, side = (average(z, t) if t else None for t in (pick(TOP), pick(SIDE)))
        if top or side:
            colors[block] = [top or side, side or top]
    colors.setdefault("water", [[int(c) for c in TINT["water_still"]]] * 2)    # its model has no textures
    path = os.path.join(OUT, f"colors-{a.version}.json")
    with open(path, "w") as f:
        json.dump({"version": a.version, "blocks": colors}, f, separators=(",", ":"), sort_keys=True)
    print(f"Wrote {path}: {len(colors)} blocks")


if __name__ == "__main__":
    main()
