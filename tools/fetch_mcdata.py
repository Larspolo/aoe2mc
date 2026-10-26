#!/usr/bin/env python3
"""
Make a compact Minecraft data file for one Java version from the Mojang data reports.

Usage:
    python tools/fetch_mcdata.py 26.3

Writes tools/mcdata/<version>.json with:
    blocks:   {block name: {property: [allowed values]}}
    entities: [entity names]
    biomes:   [biome names]
The tests use this file to check every block state, entity and biome that the converter makes.
Source: misode/mcmeta on GitHub (branch <version>-summary), which holds the data reports of each release.
(PrismarineJS is some versions behind and has old entity and biome lists.)
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = "https://raw.githubusercontent.com/misode/mcmeta/{version}-summary/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcdata")


def get(version, path):
    try:
        with urllib.request.urlopen(BASE.format(version=version) + path) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"mcmeta has no {path} for {version}: {e}")


def main(version):
    blocks = {name: props for name, (props, _default) in get(version, "blocks/data.json").items()}
    reg = get(version, "registries/data.json")
    entities, biomes = sorted(reg["entity_type"]), sorted(reg["worldgen/biome"])
    data = {"version": version, "source": BASE.format(version=version), "blocks": blocks, "entities": entities,
            "biomes": biomes}
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{version}.json")
    with open(path, "w") as f:
        json.dump(data, f, separators=(",", ":"), sort_keys=True)
    print(f"Wrote {path}: {len(blocks)} blocks, {len(entities)} entities, {len(biomes)} biomes")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "26.3")
