#!/usr/bin/env python3
"""
Read a world that aoe2mc wrote (Anvil region files). For tests and for debugging.

Usage:
    python tools/world_reader.py WORLD                 # summary: chunks, block counts, entities
    python tools/world_reader.py WORLD X Y Z           # the block state at one position
    python tools/world_reader.py WORLD --section x|z C A0 A1 Y0 Y1
        # vertical section at x = C (along z from A0 to A1) or z = C (along x), rows from Y1 down to Y0

    import world_reader as wr
    w = wr.World("MyWorld")
    w.block(10, 64, 20)        # "minecraft:grass_block"
    w.entities()               # list of entity compounds (with passengers)
"""
import io
import os
import string
import sys
import zlib
from collections import Counter

import nbtlib

MIN_Y = -64
AIR = ("air", "cave_air", "void_air")


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
        self.path = os.path.join(path, "dimensions", "minecraft", "overworld")   # 26.1 moved region/ and entities/
        self._regions = {}
        self._sections = {}                                       # (cx, cz, section Y) -> (names, indexes)

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
        key = (x >> 4, z >> 4, y >> 4)
        if key not in self._sections:                             # unpack each section one time only
            c = self.chunk(x >> 4, z >> 4)
            s = next((s for s in c["sections"] if int(s["Y"]) == y >> 4), None) if c is not None else None
            self._sections[key] = self.section_states(s) if s is not None else None
        if self._sections[key] is None:
            return None
        names, idx = self._sections[key]
        return names[idx[(y & 15) * 256 + (z & 15) * 16 + (x & 15)]]

    def section(self, axis, c, a0, a1, y0, y1):
        """Vertical section as text (#474): x = c along z (axis "x") or z = c along x (axis "z"), from a0 to a1.
        Returns (rows from y1 down to y0, one character per block, air a space, "." no chunk; legend {char: name})."""
        chars, legend, rows = {}, {}, []
        pool = string.ascii_letters + string.digits + "#%&*+=?@"
        for y in range(y1, y0 - 1, -1):
            row = ""
            for a in range(a0, a1 + 1):
                b = self.block(c, y, a) if axis == "x" else self.block(a, y, c)
                name = None if b is None else b.removeprefix("minecraft:").split("[")[0]
                if name is None or name in AIR:
                    row += "." if name is None else " "
                    continue
                if name not in chars:                             # the first free letter of the name, else of the pool
                    chars[name] = next((k for k in name.replace("_", "") + pool if k not in legend), "!")
                    legend[chars[name]] = name
                row += chars[name]
            rows.append(row)
        return rows, legend

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
        """(x, y, z, yaw) of the world spawn (the "spawn" compound of 26.x)."""
        d = self.level()
        return (*[int(v) for v in d["spawn"]["pos"]], float(d["spawn"]["yaw"]))


def main():
    w = World(sys.argv[1])
    if len(sys.argv) == 9 and sys.argv[2] == "--section":
        axis, (c, a0, a1, y0, y1) = sys.argv[3], map(int, sys.argv[4:9])
        rows, legend = w.section(axis, c, a0, a1, y0, y1)
        print(f"section {axis} = {c}, {'z' if axis == 'x' else 'x'} {a0}..{a1} (left to right), y {y1}..{y0}")
        for y, row in zip(range(y1, y0 - 1, -1), rows):
            print(f"{y:5d} |{row}|")
        for k, name in legend.items():
            print(f"  {k} {name}")
        return
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
