#!/usr/bin/env python3
"""
Make a compact Minecraft data file for one Java version from PrismarineJS minecraft-data.

Usage:
    python tools/fetch_mcdata.py 1.21.1

Writes tools/mcdata/<version>.json with:
    blocks:   {block name: {property: [allowed values]}}
    entities: [entity names]
    biomes:   [biome names]
The tests use this file to check every block state, entity and biome that the converter makes.
PrismarineJS can be some versions behind the newest Minecraft release.
"""
import json
import os
import sys
import urllib.request

BASE = "https://raw.githubusercontent.com/PrismarineJS/minecraft-data/master/data/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcdata")


def get(path):
    with urllib.request.urlopen(BASE + path) as r:
        return json.load(r)


def main(version):
    paths = get("dataPaths.json")["pc"].get(version)
    if not paths:
        sys.exit(f"PrismarineJS has no data for {version}")
    blocks = {}
    for b in get(f"{paths['blocks']}/blocks.json"):
        props = {}
        for s in b["states"]:
            if s["type"] == "bool":
                props[s["name"]] = ["true", "false"]
            elif "values" in s:
                props[s["name"]] = [str(v) for v in s["values"]]
            else:
                props[s["name"]] = [str(v) for v in range(s["num_values"])]
        blocks[b["name"]] = props
    entities = sorted(e["name"] for e in get(f"{paths['entities']}/entities.json"))
    biomes = sorted(b["name"] for b in get(f"{paths['biomes']}/biomes.json"))
    data = {"version": version, "source": {k: paths[k] for k in ("blocks", "entities", "biomes")},
            "blocks": blocks, "entities": entities, "biomes": biomes}
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{version}.json")
    with open(path, "w") as f:
        json.dump(data, f, separators=(",", ":"), sort_keys=True)
    print(f"Wrote {path}: {len(blocks)} blocks, {len(entities)} entities, {len(biomes)} biomes")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "1.21.1")
