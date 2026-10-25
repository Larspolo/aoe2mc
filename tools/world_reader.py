#!/usr/bin/env python3
"""
Read a world that aoe2mc wrote (Anvil region files). For tests and for debugging.

Usage:
    python tools/world_reader.py WORLD                 # summary: chunks, block counts, entities
    python tools/world_reader.py WORLD X Y Z           # the block state at one position

    import world_reader as wr
    w = wr.World("MyWorld")
    w.block(10, 64, 20)        # "minecraft:grass_block"
    w.entities()               # list of entity compounds (with passengers)
"""
import io
import os
import sys
import zlib
from collections import Counter

import nbtlib

MIN_Y = -64


def read_region(path):
    """{(local_x, local_z): chunk compound} of one .mca file."""
    with open(path, "rb") as f:
        data = f.read()
    out = {}
    for i in range(1024):
        loc = int.from_bytes(data[4 * i:4 * i + 3], "big")
        if not loc:
            continue
        start = loc * 4096
        length = int.from_bytes(data[start:start + 4], "big")
        kind = data[start + 4]
        if kind & 0x7F != 2:
            raise ValueError(f"{path}: chunk {i} has compression {kind & 0x7F}, expected 2 (zlib)")
        if kind & 0x80:                 # large chunk: the data is in an external c.<x>.<z>.mcc file
            rx, rz = (int(v) for v in os.path.basename(path).split(".")[1:3])
            with open(os.path.join(os.path.dirname(path), f"c.{rx * 32 + i % 32}.{rz * 32 + i // 32}.mcc"), "rb") as f:
                raw = zlib.decompress(f.read())
        else:
            raw = zlib.decompress(data[start + 5:start + 4 + length])
        out[(i % 32, i // 32)] = nbtlib.File.parse(io.BytesIO(raw))
    return out


def unpack(longs, bits, count):
    """Packed long array -> list of `count` integers (entries do not cross a long)."""
    per = 64 // bits
    mask = (1 << bits) - 1
    out = []
    for v in longs:
        v = int(v) & 0xFFFFFFFFFFFFFFFF
        for k in range(per):
            out.append((v >> (k * bits)) & mask)
    return out[:count]


def state_name(entry):
    """Palette entry -> "minecraft:name[k=v,...]". 26.3 writes {id, properties}, a string or {"": string}."""
    if not hasattr(entry, "keys"):
        return str(entry)
    if "" in entry:
        return str(entry[""])
    name = str(entry["Name"] if "Name" in entry else entry["id"])
    props = entry.get("Properties", entry.get("properties"))
    if props:
        name += "[" + ",".join(f"{k}={v}" for k, v in props.items()) + "]"
    return name


class World:
    def __init__(self, path):
        self.root = path                                          # level.dat is here
        dim = os.path.join(path, "dimensions", "minecraft", "overworld")
        self.path = dim if os.path.isdir(dim) else path           # 26.1 moved region/ and entities/
        self._regions = {}

    def _region(self, folder, rx, rz):
        key = (folder, rx, rz)
        if key not in self._regions:
            p = os.path.join(self.path, folder, f"r.{rx}.{rz}.mca")
            self._regions[key] = read_region(p) if os.path.exists(p) else {}
        return self._regions[key]

    def chunk(self, cx, cz):
        return self._region("region", cx >> 5, cz >> 5).get((cx & 31, cz & 31))

    def chunks(self, folder="region"):
        """All chunks: {(cx, cz): compound}."""
        out = {}
        d = os.path.join(self.path, folder)
        for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            _, rx, rz, _ = fn.split(".")
            for (lx, lz), c in self._region(folder, int(rx), int(rz)).items():
                out[(int(rx) * 32 + lx, int(rz) * 32 + lz)] = c
        return out

    def section_states(self, section):
        """(palette names, list of 4096 palette indexes) of one section."""
        bs = section["block_states"]
        names = [state_name(e) for e in bs["palette"]]
        if "data" not in bs:
            return names, [0] * 4096
        bits = max(4, (len(names) - 1).bit_length())
        return names, unpack(bs["data"], bits, 4096)

    def block(self, x, y, z):
        c = self.chunk(x >> 4, z >> 4)
        if c is None:
            return None
        for s in c["sections"]:
            if int(s["Y"]) == y >> 4:
                names, idx = self.section_states(s)
                return names[idx[(y & 15) * 256 + (z & 15) * 16 + (x & 15)]]
        return None

    def palette(self):
        """Counter of every block state name in the palettes of all sections (each name once per section)."""
        n = Counter()
        for c in self.chunks().values():
            for s in c["sections"]:
                n.update(state_name(e) for e in s["block_states"]["palette"])
        return n

    def entities(self, flat=True):
        """All entities. flat=True also lists the passengers (riders) as separate entries."""
        out = []

        def walk(e):
            out.append(e)
            if flat:
                for p in e.get("Passengers", []):
                    walk(p)
        for c in self.chunks("entities").values():
            for e in c["Entities"]:
                walk(e)
        return out

    def level(self):
        return nbtlib.load(os.path.join(self.root, "level.dat"))["Data"]

    def spawn(self):
        """(x, y, z, yaw) of the world spawn. 26.x has a "spawn" compound, 1.21.1 has SpawnX ... SpawnAngle."""
        d = self.level()
        if "spawn" in d:
            return (*[int(v) for v in d["spawn"]["pos"]], float(d["spawn"]["yaw"]))
        return int(d["SpawnX"]), int(d["SpawnY"]), int(d["SpawnZ"]), float(d["SpawnAngle"])


def main():
    w = World(sys.argv[1])
    if len(sys.argv) == 5:
        print(w.block(*map(int, sys.argv[2:5])))
        return
    chunks = w.chunks()
    print(f"{len(chunks)} chunks, level {w.level()['LevelName']} (DataVersion {w.level()['DataVersion']})")
    for name, k in w.palette().most_common(25):
        print(f"  {k:6d} sections with {name}")
    ents = Counter(str(e["id"]) for e in w.entities())
    print("entities:", dict(ents.most_common()))


if __name__ == "__main__":
    main()
