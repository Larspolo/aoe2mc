"""Reader of old AoE2 scenarios (.scn of The Age of Kings: formats 1.18 to 1.20, #3860; .scx: format 1.21 of The
Conquerors; .scx and .aoe2scenario of the HD Edition: formats 1.22 to 1.26, #3862; the first DE formats 1.32 to 1.35, #5072),
without the DE editor (#311).

A port of the reader of genie-scx (genie-rs, GPL-3.0; crates/genie-scx/src/format.rs, map.rs, player.rs) for the
fields that aoe2mc needs. Layout: docs/campaign-formats.md, "The old scenario format".

    import scx
    s = scx.read("old.scx")      # dict: width, height, terrain [x, y], elevation [x, y], players {id: {civ, color, view}},
                                 # objects [{player, id, type, x, y, angle, garrisoned_in}]
"""
import struct
import zlib

import numpy as np

import units

FORMATS = {b"1.18", b"1.19", b"1.20", b"1.21",        # format versions that this reader knows (the object frame from 1.15,
           b"1.22", b"1.23", b"1.24", b"1.25", b"1.26",  # "garrisoned in" from 1.13: one object layout); 1.22 to 1.26:
           b"1.32", b"1.33", b"1.34", b"1.35"}           # the HD Edition (.aoe2scenario too, #3862); 1.32 to 1.35: the
                                                        # first DE files, older than the layouts of AoE2ScenarioParser (#5072)
CIVS = [r["name"] for r in units.rows("scx_civs.jsonl")]   # the index is the civilization ID, the DE IDs too


class ScxError(ValueError):
    """A file that this reader cannot read."""


class Stream:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def take(self, n):
        if self.pos + n > len(self.data):
            raise ScxError(f"the file ends at byte {len(self.data)}, the reader needs {self.pos + n}")
        b = self.data[self.pos:self.pos + n]
        self.pos += n
        return b

    def unpack(self, fmt):
        return struct.unpack("<" + fmt, self.take(struct.calcsize("<" + fmt)))

    def i32(self, n=None):
        return self.unpack("i")[0] if n is None else self.unpack(f"{n}i")

    def u32(self):
        return self.unpack("I")[0]

    def f32(self):
        return self.unpack("f")[0]

    def str16(self):
        """A string with a u16 length (the text can end with a 0 byte)."""
        return self.take(self.unpack("H")[0]).split(b"\0")[0].decode("latin-1")

    def skip(self, n):
        self.take(n)


def tribe_scen(s):
    """Read TribeScen (genie-scx RGEScen and TribeScen) up to the map. Returns {player: civilization ID}."""
    v = round(s.f32(), 4)                   # the data version: 1.22 in AoC scenarios of format 1.21; DE: the format
    if not 1.14 <= v < 1.38:
        raise ScxError(f"unknown scenario data version {v} (this reader knows 1.14 to 1.37)")
    s.skip(16 * 256)                        # player names
    if v > 1.16:
        s.skip(16 * 4)                      # string table IDs of the names
    props = [s.i32(4) for _ in range(16)]   # active, human, civilization, posture
    s.skip(1 + 2 + 2 + 4 + (16 * 4 if v >= 1.28 else 0))   # conquest victory, timeline count and flag, old time; DE: civ locks
    s.str16()                               # file name
    s.skip(5 * 4 + (4 if v >= 1.22 else 0))  # string table IDs of the texts
    for _ in range(5 + (v >= 1.22) + 3 + 1):  # description, hints, win, loss, history, scout, 3 cinematics, bitmap name
        s.str16()
    _, w, h, _ = s.unpack("IIIH")           # the bitmap of the mission
    if w > 0 and h > 0:
        s.skip(40 + 256 * 4 + h * ((w + 3) & ~3))
    for _ in range(16 * 3):                 # build lists, city plans, AI rules
        s.str16()
    for _ in range(16):                     # the files of each player
        s.skip(sum(s.i32(3)))
    if v >= 1.20:
        s.skip(16)                          # AI rule types
    s.i32()                                 # separator -99
    s.skip(16 * 4 * (6 if v >= 1.17 else 4) + (16 * 4 if v >= 1.24 else 0))   # start resources (and colors)
    s.i32()
    s.skip(6 * 4 + 4 + 3 * 4)               # victory info, "all" flag, victory type, score, time
    s.skip(16 * 16 * 4 + 16 * 12 * 60)      # diplomacy, old victory conditions
    s.i32()
    s.skip(16 * 4)                          # allied victory
    s.skip(4 if v >= 1.24 else 4 if abs(v - 1.23) < 1e-3 else 0)   # team settings
    if v >= 1.28:                           # DE: disabled techs, units, buildings (counts, then lists of that length)
        for _ in range(3):
            s.skip(4 * sum(s.i32(16)))
    elif v >= 1.18:                         # disabled techs, units, buildings (counts, then fixed lists)
        s.skip(16 * 4 + 16 * 30 * 4 + 16 * 4 + 16 * 30 * 4 + 16 * 4 + 16 * (30 if v >= 1.25 else 20) * 4)
    else:
        s.skip(16 * 20 * 4)
    s.skip(4 + 2 * 4 + 16 * 4)              # combat mode, naval mode, all techs, start ages
    s.i32()
    if v >= 1.19:
        s.skip(8)                           # view
    if v >= 1.21:
        s.skip(4)                           # map type
    if v >= 1.24:
        s.skip(16)                          # base priorities
    if v >= 1.35:
        s.skip(4)                           # the number of triggers
    for since in (1.30, 1.32):              # water definition, color mood: a u16 signature, then the text
        if v >= since:
            s.skip(2)
            s.str16()
    s.skip((v >= 1.36) + (v >= 1.37))       # collide and correct, villager force drop
    return {p: props[p - 1][2] for p in range(1, 17) if props[p - 1][0]}


# The bytes of a tile of each map version (genie-scx map.rs, #3861): terrain, elevation, zone; from version 1 also
# the mask type and the layered terrain (u16 each). Version 2 adds a "no waves" byte before the size.
MAP_TILE = {0: 3, 1: 7, 2: 7}


def read_map(s, path):
    """The terrain and elevation ([x, y]) of the map part: format 1.21, or a versioned map (marker 0xDEADF00D, HD)."""
    w, tile = s.u32(), 3
    if w == 0xDEADF00D:
        version = s.u32()
        if version not in MAP_TILE:
            raise ScxError(f"{path}: map version {version} is not supported (this reader knows "
                           f"{', '.join(map(str, MAP_TILE))})")
        s.skip(1 if version >= 2 else 0)        # "no waves"
        w, tile = s.u32(), MAP_TILE[version]
    h = s.u32()
    if not (0 < w <= 500 and 0 < h <= 500):
        raise ScxError(f"{path}: map size {w} x {h} is not possible: the file has another layout")
    tiles = np.frombuffer(s.take(w * h * tile), np.uint8).reshape(h, w, tile)    # rows of y, then x
    terrain = tiles[:, :, 0].T.astype(np.int16)                                  # [x, y], as read_scenario
    return terrain, tiles[:, :, 1].view(np.int8).T.astype(np.float32)


def body_start(data):
    """The offset of the compressed part. HD files can write a header length of 0 (#3847): then the header ends
    after its last field, as in genie-scx (header.rs, read_from), so read the fields one by one."""
    u = lambda p: struct.unpack_from("<I", data, p)[0]
    if u(4):
        return 8 + u(4)
    p = 8
    version = u(p)
    p += 4
    if version >= 2:                         # the time stamp
        p += 4
    p += 4 + u(p)                            # the description: a length-prefixed string
    p += 8                                   # any SP victory, active player count
    if version > 2:                          # DLC options: a data set (after a version, unless 0 or 1), dependencies
        p += 4
        if struct.unpack_from("<i", data, p - 4)[0] not in (0, 1):
            p += 4
        p += 4 + 4 * u(p)
    if version >= 5:                         # the author name and the number of triggers
        p += 4 + u(p) + 4
    return p


def scenario_players(s, civs, tail=0):
    """The scenario player data: {player: {civ, color, view}} of the players with a civilization."""
    players = {0: {"civ": "GAIA", "color": None, "view": None}}
    for p in range(1, s.u32()):
        s.str16()
        view = (s.f32(), s.f32())
        s.skip(2 * 2 + 1)                   # location, allied victory
        s.skip(s.unpack("h")[0])            # diplomacy
        s.skip(9 * 4)                       # unit diplomacy
        color = s.i32()
        cv = s.f32()
        count, _ = s.unpack("iB")
        s.skip(count * 44)                  # victory conditions
        if cv >= 1.0:
            s.i32()
            points = s.i32()
            s.skip((8 if cv >= 2.0 else 0) + points * (32 if cv >= 2.0 else 24))
        s.skip(tail)                        # format 1.35: an i32 (-1) ends each player (special_map_*, #5209)
        civ = civs.get(p)
        if civ is not None:
            players[p] = {"civ": CIVS[civ] if 0 <= civ < len(CIVS) else f"CIV_{civ}", "color": color,
                          "view": view if min(view) >= 0 else None}
    return players


def read(path):
    with open(path, "rb") as f:
        data = f.read()
    fmt = data[:4]
    if fmt not in FORMATS:
        raise ScxError(f"{path}: scenario format {fmt.decode('latin-1')!r} is not supported "
                       f"(this reader knows {', '.join(sorted(f.decode() for f in FORMATS))})")
    try:
        s = Stream(zlib.decompress(data[body_start(data):], -15))
    except zlib.error as e:
        raise ScxError(f"{path}: the compressed part does not decompress ({e})") from None
    s.i32()                                 # next object ID
    civs = tribe_scen(s)
    terrain, elevation = read_map(s, path)

    n = s.u32()
    s.skip((n - 1) * (6 if fmt < b"1.20" else 7) * 4)   # world player data: resources, population from 1.20 (genie-scx)
    # The colors and start views are in the scenario player data: after the objects before format 1.35, else before
    # (the special_map_* files of format 1.35 have it before, #5209)
    if fmt >= b"1.35":
        players = scenario_players(s, civs, 4 if fmt == b"1.35" else 0)
    objects = []
    for p in range(n):                      # objects: x, y, z, ID, type, state, angle, frame, garrisoned in
        for _ in range(s.u32()):
            x, y, _, ref, kind, _, angle, _, holder = s.unpack("fffiHBfhi")
            objects.append({"player": p, "id": ref, "type": kind, "x": x, "y": y, "angle": angle,
                            "garrisoned_in": holder if holder > 0 else None})     # 0 and -1: not garrisoned
    if fmt < b"1.35":
        players = scenario_players(s, civs)
    return {"format": fmt.decode(), "width": terrain.shape[0], "height": terrain.shape[1], "terrain": terrain, "elevation": elevation,
            "players": players, "objects": objects}
