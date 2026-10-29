"""
Building designs for aoe2mc.

Each building is drawn on a Canvas in local coordinates:
    x = 0 .. w-1 (west -> east), z = 0 .. w-1 (north -> south), y = 0 is the floor level.
The front (main door) is on the south side (z = w-1). In the AoE2 view the south and east sides
face the camera. All sizes scale with the footprint width w (= tiles * tile-size).
"""
import math
from dataclasses import dataclass

import numpy as np

import units

QUOIN = {"stone_bricks": "polished_andesite", "cut_sandstone": "chiseled_sandstone", "mud_bricks": "packed_mud",
         "cut_red_sandstone": "chiseled_red_sandstone", "mossy_stone_bricks": "stone_bricks",
         "smooth_sandstone": "cut_sandstone", "terracotta": "brown_terracotta"}

WOODS = ("oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry", "crimson", "warped")


def family(name):
    """Roof material -> (stairs, slab, full block)."""
    if name in WOODS:
        return f"{name}_stairs", f"{name}_slab", f"{name}_planks"
    full = name + "s" if name.endswith(("brick", "tile")) else name
    return f"{name}_stairs", f"{name}_slab", full


def stair(st, facing, shape="straight", half="bottom"):
    return f"{st}[facing={facing},half={half},shape={shape}]"


# --------------------------------------------------------------------------------------------
# Architecture sets
# --------------------------------------------------------------------------------------------
@dataclass
class Style:
    plaster: str      # light wall fill
    timber: str       # vertical posts (a log type)
    beam: str         # horizontal beams (a log type)
    wood: str         # planks for wooden walls and decks
    stone: str        # main stone
    stone2: str       # rough stone (foundations, paths)
    floor: str
    roof: str         # roof material family
    shape: str        # gable | hip | flat | asian
    dome: str
    wonder: str       # cathedral | mosque | pagoda | pyramid | temple
    mill: str         # windmill | granary
    domes: bool = False   # religious buildings get domes instead of spires
    accent: str = "polished_andesite"       # trim: base rows, bands, cornices, caps of fortified walls
    accent_wall: str = "stone_brick_wall"   # low walls and parapets
    framing: str = "timber"                 # timber = half-timbered walls; bands = plaster with stone bands
    merlon: str = ""                        # merlons of walls and castles (empty = main stone)
    eaves: bool = False                     # flat roofs get a sloped overhang (chhajja)
    torons: bool = False                    # wooden beams that stick out of the walls (Sahel mud architecture)


ARCH = {
    "western": Style("white_terracotta", "dark_oak_log", "stripped_dark_oak_log", "spruce_planks",
                     "stone_bricks", "cobblestone", "spruce_planks", "dark_oak", "gable",
                     "deepslate_tiles", "cathedral", "windmill"),
    "central": Style("white_terracotta", "spruce_log", "stripped_spruce_log", "spruce_planks",
                     "stone_bricks", "cobblestone", "spruce_planks", "red_sandstone", "gable",
                     "deepslate_tiles", "cathedral", "windmill"),
    "mediterranean": Style("smooth_sandstone", "stripped_oak_log", "stripped_oak_log", "oak_planks",
                           "stone_bricks", "cobblestone", "oak_planks", "brick", "hip",
                           "bricks", "cathedral", "windmill"),
    "middle_eastern": Style("smooth_sandstone", "stripped_acacia_log", "stripped_acacia_log", "acacia_planks",
                            "cut_sandstone", "sandstone", "smooth_sandstone", "smooth_sandstone", "flat",
                            "light_blue_terracotta", "mosque", "granary", domes=True,
                            accent="light_blue_terracotta", accent_wall="sandstone_wall", framing="bands",
                            eaves=False),
    "south_asian": Style("smooth_sandstone", "stripped_acacia_log", "stripped_acacia_log", "acacia_planks",
                         "cut_sandstone", "red_sandstone", "smooth_sandstone", "red_sandstone", "flat",
                         "smooth_quartz", "mosque", "granary", domes=True,
                         accent="cut_red_sandstone", accent_wall="red_sandstone_wall", framing="bands",
                         merlon="cut_red_sandstone", eaves=True),
    "african": Style("terracotta", "stripped_oak_log", "stripped_oak_log", "oak_planks",
                     "mud_bricks", "packed_mud", "packed_mud", "mud_brick", "flat",
                     "terracotta", "mosque", "granary", domes=True,
                     accent="brown_terracotta", accent_wall="mud_brick_wall", framing="bands", torons=True),
    "east_asian": Style("white_terracotta", "stripped_crimson_stem", "stripped_dark_oak_log", "dark_oak_planks",
                        "stone_bricks", "cobblestone", "dark_oak_planks", "spruce", "asian",
                        "deepslate_tiles", "pagoda", "granary"),
    "southeast_asian": Style("smooth_sandstone", "stripped_jungle_log", "stripped_jungle_log", "jungle_planks",
                             "sandstone", "cobblestone", "jungle_planks", "red_sandstone", "asian",
                             "sandstone", "temple", "granary"),
    "mesoamerican": Style("smooth_stone", "stripped_jungle_log", "stripped_jungle_log", "jungle_planks",
                          "mossy_stone_bricks", "cobblestone", "smooth_stone", "stone_brick", "hip",
                          "mossy_stone_bricks", "pyramid", "granary"),
}

CIV_ARCH = {
    "western": "BRITONS FRANKS CELTS BURGUNDIANS SICILIANS SAXONS",
    "central": "GOTHS TEUTONS VIKINGS HUNS VARANGIANS DANES SLAVS MAGYARS BULGARIANS LITHUANIANS "
               "POLES BOHEMIANS",
    "mediterranean": "BYZANTINES SPANISH ITALIANS PORTUGUESE ROMANS ARMENIANS GEORGIANS ATHENIANS "
                     "SPARTANS MACEDONIANS THRACIANS",
    "middle_eastern": "PERSIANS SARACENS TURKS BERBERS ACHAEMENIDS TATARS CUMANS",
    "south_asian": "HINDUSTANIS DRAVIDIANS BENGALIS GURJARAS PURU",
    "african": "ETHIOPIANS MALIANS",
    "east_asian": "JAPANESE CHINESE KOREANS MONGOLS SHU WU WEI JURCHENS KHITANS",
    "southeast_asian": "KHMER MALAY BURMESE VIETNAMESE",
    "mesoamerican": "AZTECS MAYANS INCAS MUISCA MAPUCHE TUPI",
}
CIV_TO_ARCH = {civ: arch for arch, civs in CIV_ARCH.items() for civ in civs.split()}

COLOR_NAMES = ["blue", "red", "green", "yellow", "cyan", "purple", "gray", "orange"]


# --------------------------------------------------------------------------------------------
# Canvas: a small block grid with drawing tools. -1 means "do not change".
# --------------------------------------------------------------------------------------------
class Canvas:
    def __init__(self, blocks, w, height, margin=3, below=0):
        self.B, self.w, self.m, self.below, self.height = blocks, w, margin, below, height
        self.rng = np.random.default_rng(0)
        self.doors = []                 # (x, z) of door blocks, the space in front stays free
        self.trapdoor = "spruce_trapdoor"
        self.goods = ()                 # item names for the shelves of the design (place_building fills them, #526)
        self.a = np.full((w + 2 * margin, height + below, w + 2 * margin), -1, np.int32)

    def id(self, b):
        return int(b) if isinstance(b, (int, np.integer)) else self.B(b)    # -1 = do not change

    def box(self, x0, x1, y0, y1, z0, z1, b):
        m = self.m
        x0, x1 = max(x0 + m, 0), min(x1 + m, self.a.shape[0])
        z0, z1 = max(z0 + m, 0), min(z1 + m, self.a.shape[2])
        y0, y1 = max(y0 + self.below, 0), min(y1 + self.below, self.a.shape[1])
        if x0 < x1 and y0 < y1 and z0 < z1:
            self.a[x0:x1, y0:y1, z0:z1] = self.id(b)

    def set(self, x, y, z, b):
        self.box(x, x + 1, y, y + 1, z, z + 1, b)

    def get(self, x, y, z):
        try:
            return self.a[x + self.m, y + self.below, z + self.m]
        except IndexError:
            return -1

    def walls(self, x0, x1, y0, y1, z0, z1, b, t=1):
        """Four walls of thickness t around the area x0..x1-1, z0..z1-1."""
        self.box(x0, x1, y0, y1, z0, z0 + t, b)
        self.box(x0, x1, y0, y1, z1 - t, z1, b)
        self.box(x0, x0 + t, y0, y1, z0, z1, b)
        self.box(x1 - t, x1, y0, y1, z0, z1, b)

    def room(self, x0, x1, z0, z1, y0, h, wall, floor=None, corner=None):
        """Floor at y0, walls from y0+1 to y0+h, empty inside. Stone walls get corner stones (quoins)."""
        if floor:
            self.box(x0, x1, y0, y0 + 1, z0, z1, floor)
        self.box(x0, x1, y0 + 1, y0 + h + 1, z0, z1, "air")
        self.walls(x0, x1, y0 + 1, y0 + h + 1, z0, z1, wall)
        if corner:
            for x in (x0, x1 - 1):
                for z in (z0, z1 - 1):
                    self.box(x, x + 1, y0 + 1, y0 + h + 1, z, z + 1, corner)
        elif wall in QUOIN:
            for x in (x0, x1 - 1):
                for z in (z0, z1 - 1):
                    for y in range(y0 + 1, y0 + h + 1, 2):
                        self.set(x, y, z, QUOIN[wall])

    def timber_room(self, x0, x1, z0, z1, y0, h, st, low_stone=1):
        """Half-timbered walls: plaster with dark posts and beams (low_stone: stone rows at the bottom).
        Styles with framing "bands" get plaster walls with a stone base, a cornice and pilasters instead."""
        if st.framing == "bands":
            return self.banded_room(x0, x1, z0, z1, y0, h, st, low_stone)
        self.room(x0, x1, z0, z1, y0, h, st.plaster, st.floor, corner=st.timber)
        if low_stone:
            self.walls(x0, x1, y0 + 1, y0 + 1 + low_stone, z0, z1, st.stone)
        top = y0 + h
        self.box(x0, x1, top, top + 1, z0, z0 + 1, f"{st.beam}[axis=x]")
        self.box(x0, x1, top, top + 1, z1 - 1, z1, f"{st.beam}[axis=x]")
        self.box(x0, x0 + 1, top, top + 1, z0 + 1, z1 - 1, f"{st.beam}[axis=z]")
        self.box(x1 - 1, x1, top, top + 1, z0 + 1, z1 - 1, f"{st.beam}[axis=z]")
        if h >= 6:   # beam between the two floors
            mid = y0 + h // 2
            self.walls(x0, x1, mid, mid + 1, z0, z1, f"{st.beam}[axis=x]")
            self.box(x0, x0 + 1, mid, mid + 1, z0 + 1, z1 - 1, f"{st.beam}[axis=z]")   # log ends do not show outside
            self.box(x1 - 1, x1, mid, mid + 1, z0 + 1, z1 - 1, f"{st.beam}[axis=z]")
        for x in range(x0 + 3, x1 - 2, 3):          # extra posts
            for z in (z0, z1 - 1):
                self.box(x, x + 1, y0 + 1 + low_stone, top, z, z + 1, st.timber)
        for z in range(z0 + 3, z1 - 2, 3):
            for x in (x0, x1 - 1):
                self.box(x, x + 1, y0 + 1 + low_stone, top, z, z + 1, st.timber)

    def banded_room(self, x0, x1, z0, z1, y0, h, st, low_stone=1):
        self.room(x0, x1, z0, z1, y0, h, st.plaster, st.floor, corner=st.accent)
        self.walls(x0, x1, y0 + 1, y0 + 1 + max(1, low_stone), z0, z1, st.accent)      # base
        self.walls(x0, x1, y0 + h, y0 + h + 1, z0, z1, st.accent)                       # cornice
        if h >= 6:
            self.walls(x0, x1, y0 + h // 2, y0 + h // 2 + 1, z0, z1, st.accent)
        for x in range(x0 + 4, x1 - 3, 4):                                             # pilasters
            for z in (z0, z1 - 1):
                self.box(x, x + 1, y0 + 1, y0 + h, z, z + 1, st.accent)
        for z in range(z0 + 4, z1 - 3, 4):
            for x in (x0, x1 - 1):
                self.box(x, x + 1, y0 + 1, y0 + h, z, z + 1, st.accent)
        if st.torons:                                                                  # beams sticking out
            y = y0 + h - 1
            for x in range(x0 + 1, x1 - 1, 2):
                self.set(x, y, z0 - 1, f"{st.beam}[axis=z]"); self.set(x, y, z1, f"{st.beam}[axis=z]")
            for z in range(z0 + 1, z1 - 1, 2):
                self.set(x0 - 1, y, z, f"{st.beam}[axis=x]"); self.set(x1, y, z, f"{st.beam}[axis=x]")

    def windows(self, x0, x1, z0, z1, y, b="glass_pane", step=3, sides="nesw", height=1):
        """Windows in the walls of the area. Glass windows get shutters and a sill on the outside."""
        spots = []
        for x in range(x0 + 2, x1 - 2, step):
            if "n" in sides: spots.append((x, z0, 0, -1, "north"))
            if "s" in sides: spots.append((x, z1 - 1, 0, 1, "south"))
        for z in range(z0 + 2, z1 - 2, step):
            if "w" in sides: spots.append((x0, z, -1, 0, "west"))
            if "e" in sides: spots.append((x1 - 1, z, 1, 0, "east"))
        for x, z, dx, dz, face in spots:
            self.box(x, x + 1, y, y + height, z, z + 1, b)
            if b != "glass_pane":
                continue
            ox, oz = x + dx, z + dz                                  # the air in front of the window
            r = self.rng.random()
            if r < 0.55:                                             # open shutters left and right
                for sx, sz in ((dz, dx), (-dz, -dx)):
                    for yy in range(y, y + height):
                        if self.get(ox + sx, yy, oz + sz) == -1:
                            self.set(ox + sx, yy, oz + sz, f"{self.trapdoor}[facing={face},half=bottom,open=true]")
            if r < 0.35 or r > 0.85:                                 # sill, sometimes with flowers
                if self.get(ox, y - 1, oz) == -1:
                    self.set(ox, y - 1, oz, f"{self.trapdoor}[facing={face},half=top,open=false]")
                    if r > 0.85 and self.get(ox, y, oz) == -1:
                        self.set(ox, y, oz, ["potted_red_tulip", "potted_poppy", "potted_blue_orchid",
                                             "potted_fern"][int(self.rng.integers(4))])

    def door(self, x, y, z, facing="south", wood="spruce"):
        self.set(x, y, z, f"{wood}_door[facing={facing},half=lower,hinge=left,open=false]")
        self.set(x, y + 1, z, f"{wood}_door[facing={facing},half=upper,hinge=left,open=false]")
        self.doors.append((x, z))

    def bed(self, x, y, z, color, facing="north"):
        """A bed with its head at (x, z) and its foot one block back from `facing`."""
        dx, dz = {"north": (0, 1), "south": (0, -1), "west": (1, 0), "east": (-1, 0)}[facing]
        self.set(x, y, z, f"{color}_bed[facing={facing},occupied=false,part=head]")
        self.set(x + dx, y, z + dz, f"{color}_bed[facing={facing},occupied=false,part=foot]")

    def free_bed(self, y, spots, color="straw", open_=False):
        """The bed of the first spot (x, z, facing of the head) whose two cells are air (`open_`: also empty, for
        an open yard), with air above, on a floor and not next to a door. Returns False when no spot fits (small --tile-size)."""
        ok = (self.id("air"), -1) if open_ else (self.id("air"),)
        near = {(x + dx, z + dz) for x, z in self.doors for dx in (-1, 0, 1) for dz in (-1, 0, 1)}
        for x, z, f in spots:
            dx, dz = {"north": (0, 1), "south": (0, -1), "west": (1, 0), "east": (-1, 0)}[f]
            cells = ((x, z), (x + dx, z + dz))
            if all(0 <= a < self.w and 0 <= b < self.w and (a, b) not in near and self.get(a, y, b) in ok
                   and self.get(a, y - 1, b) not in ok and self.get(a, y + 1, b) in ok for a, b in cells):
                self.bed(x, y, z, color, f)
                return True
        return False

    def banner(self, x, y, z, color, facing="south"):
        """A wall banner in front of the wall block next to it."""
        self.set(x, y, z, f"{color}_wall_banner[facing={facing}]")

    def flag(self, x, y, z, color, h=2):
        self.box(x, x + 1, y, y + h, z, z + 1, "oak_fence")
        self.set(x, y + h, z, f"{color}_banner[rotation=4]")

    def furniture(self, items):
        """Furniture (x, y, z, state) inside a room: only into air, and the cells next to a door stay free.
        Small sizes (--tile-size) have small rooms: things that hit a wall are left out."""
        air = self.id("air")
        free = {(x + dx, z + dz) for x, z in self.doors for dx in (-1, 0, 1) for dz in (-1, 0, 1)}
        for x, y, z, b in items:
            if (x, z) not in free and self.get(x, y, z) == air:
                self.set(x, y, z, b)

    # ---- roofs ----------------------------------------------------------------------------
    def gable(self, x0, x1, z0, z1, y, mat, fill=None, axis="x"):
        """Pitched roof over x0..x1-1, z0..z1-1 starting at height y. The ridge runs along `axis`.
        fill = (x0, x1, z0, z1, block): wall area whose gable ends get filled. Returns the ridge y."""
        st, sl, full = family(mat)
        if axis == "x":
            d = z1 - z0
            for i in range((d + 1) // 2):
                a, b, yy = z0 + i, z1 - 1 - i, y + i
                if a == b:
                    self.box(x0, x1, yy, yy + 1, a, a + 1, f"{sl}[type=bottom]")
                else:
                    self.box(x0, x1, yy, yy + 1, a, a + 1, stair(st, "south"))
                    self.box(x0, x1, yy, yy + 1, b, b + 1, stair(st, "north"))
                if fill and i > 0:
                    fx0, fx1, fz0, fz1, fb = fill
                    lo, hi = max(a + 1, fz0), min(b, fz1)
                    for fx in (fx0, fx1 - 1):
                        self.box(fx, fx + 1, yy, yy + 1, lo, hi, fb)
            return y + (d + 1) // 2 - 1
        d = x1 - x0
        for i in range((d + 1) // 2):
            a, b, yy = x0 + i, x1 - 1 - i, y + i
            if a == b:
                self.box(a, a + 1, yy, yy + 1, z0, z1, f"{sl}[type=bottom]")
            else:
                self.box(a, a + 1, yy, yy + 1, z0, z1, stair(st, "east"))
                self.box(b, b + 1, yy, yy + 1, z0, z1, stair(st, "west"))
            if fill and i > 0:
                fx0, fx1, fz0, fz1, fb = fill
                lo, hi = max(a + 1, fx0), min(b, fx1)
                for fz in (fz0, fz1 - 1):
                    self.box(lo, hi, yy, yy + 1, fz, fz + 1, fb)
        return y + (d + 1) // 2 - 1

    def hip(self, x0, x1, z0, z1, y, mat, layers=999, flare=False):
        """Hipped roof (a pyramid on square plans). Returns the top y."""
        st, sl, full = family(mat)
        i = 0
        while x1 > x0 and z1 > z0 and i < layers:
            yy = y + i
            if x1 - x0 == 1 or z1 - z0 == 1:
                self.box(x0, x1, yy, yy + 1, z0, z1, f"{sl}[type=bottom]")
                return yy
            self.box(x0 + 1, x1 - 1, yy, yy + 1, z0, z0 + 1, stair(st, "south"))
            self.box(x0 + 1, x1 - 1, yy, yy + 1, z1 - 1, z1, stair(st, "north"))
            self.box(x0, x0 + 1, yy, yy + 1, z0 + 1, z1 - 1, stair(st, "east"))
            self.box(x1 - 1, x1, yy, yy + 1, z0 + 1, z1 - 1, stair(st, "west"))
            self.set(x0, yy, z0, stair(st, "south", "outer_left"))
            self.set(x1 - 1, yy, z0, stair(st, "south", "outer_right"))
            self.set(x0, yy, z1 - 1, stair(st, "north", "outer_right"))
            self.set(x1 - 1, yy, z1 - 1, stair(st, "north", "outer_left"))
            if flare and i == 0:           # upturned corners (East Asian roofs)
                for cx, cz in ((x0, z0), (x1 - 1, z0), (x0, z1 - 1), (x1 - 1, z1 - 1)):
                    self.set(cx, yy + 1, cz, f"{sl}[type=bottom]")
            if x1 - x0 == 2 or z1 - z0 == 2:
                return yy
            x0, x1, z0, z1, i = x0 + 1, x1 - 1, z0 + 1, z1 - 1, i + 1
        return y + i - 1

    def flat_roof(self, x0, x1, z0, z1, y, mat, parapet=None):
        st, sl, full = family(mat)
        self.box(x0, x1, y, y + 1, z0, z1, full)
        if parapet:
            self.walls(x0, x1, y + 1, y + 2, z0, z1, parapet)
            for x in range(x0, x1, 2):
                self.set(x, y + 2, z0, parapet); self.set(x, y + 2, z1 - 1, parapet)
            for z in range(z0, z1, 2):
                self.set(x0, y + 2, z, parapet); self.set(x1 - 1, y + 2, z, parapet)
        return y + 1

    def styled_flat_roof(self, x0, x1, z0, z1, y, st):
        """Flat roof with a parapet, and (depending on the style) a sloped eave and small corner kiosks."""
        stairs, slab, full = family(st.roof)
        self.box(x0, x1, y, y + 1, z0, z1, full)
        if st.eaves:                                   # chhajja: a sloped overhang below the roof edge
            yy = y - 1
            self.box(x0, x1, yy, yy + 1, z0 - 1, z0, stair(stairs, "south", half="top"))
            self.box(x0, x1, yy, yy + 1, z1, z1 + 1, stair(stairs, "north", half="top"))
            self.box(x0 - 1, x0, yy, yy + 1, z0, z1, stair(stairs, "east", half="top"))
            self.box(x1, x1 + 1, yy, yy + 1, z0, z1, stair(stairs, "west", half="top"))
            self.box(x0 - 1, x1 + 1, y, y + 1, z0 - 1, z0, f"{slab}[type=bottom]")
            self.box(x0 - 1, x1 + 1, y, y + 1, z1, z1 + 1, f"{slab}[type=bottom]")
            self.box(x0 - 1, x0, y, y + 1, z0, z1, f"{slab}[type=bottom]")
            self.box(x1, x1 + 1, y, y + 1, z0, z1, f"{slab}[type=bottom]")
        self.walls(x0, x1, y + 1, y + 2, z0, z1, st.accent_wall)
        if st.domes and x1 - x0 >= 8 and z1 - z0 >= 8:  # chhatri: small domed kiosks on the corners
            for cx in (x0 + 1, x1 - 3):
                for cz in (z0 + 1, z1 - 3):
                    for px in (cx, cx + 1):
                        for pz in (cz, cz + 1):
                            self.set(px, y + 1, pz, st.accent_wall)
                    self.box(cx, cx + 2, y + 2, y + 3, cz, cz + 2, f"{family(st.roof)[1]}[type=bottom]")
                    self.box(cx, cx + 2, y + 2, y + 3, cz, cz + 2, st.dome)
                    self.set(cx, y + 3, cz, "lightning_rod")
        return y + 1

    def roof(self, x0, x1, z0, z1, y, st, fill_block=None, axis=None, over=1):
        """Roof in the style of the architecture set over the walls x0..x1-1, z0..z1-1 (walls top = y-1)."""
        if st.shape == "flat":
            return self.styled_flat_roof(x0, x1, z0, z1, y, st)
        X0, X1, Z0, Z1 = x0 - over, x1 + over, z0 - over, z1 + over
        if st.shape in ("hip", "asian"):
            return self.hip(X0, X1, Z0, Z1, y - 1 + (0 if over else 1), st.roof, flare=st.shape == "asian")
        if axis is None:
            axis = "x" if (x1 - x0) >= (z1 - z0) else "z"
        return self.gable(X0, X1, Z0, Z1, y - 1 + (0 if over else 1), st.roof,
                          fill=(x0, x1, z0, z1, fill_block or st.plaster), axis=axis)

    # ---- round shapes ---------------------------------------------------------------------
    def disc_mask(self, cx, cz, r):
        xs = np.arange(-self.m, self.w + self.m)
        X, Z = np.meshgrid(xs, xs, indexing="ij")
        return (X - cx) ** 2 + (Z - cz) ** 2 <= r * r + 0.5, X, Z

    def cylinder(self, cx, cz, r, y0, y1, b, hollow=False):
        m, X, Z = self.disc_mask(cx, cz, r)
        if hollow:
            inner, _, _ = self.disc_mask(cx, cz, r - 1)
            self._fill_mask(inner, y0, y1, "air")
            m = m & ~inner
        self._fill_mask(m, y0, y1, b)

    def _fill_mask(self, mask, y0, y1, b):
        y0, y1 = max(y0 + self.below, 0), min(y1 + self.below, self.a.shape[1])
        if y0 < y1:
            sub = self.a[:, y0:y1, :]
            sub[np.broadcast_to(mask[:, None, :], sub.shape)] = self.id(b)

    def cone(self, cx, cz, r, y, b, step=1):
        """Pointed roof: discs that get smaller. Returns the top y."""
        k = 0
        while r > 0.3:
            self.cylinder(cx, cz, r, y + k, y + k + step, b)
            r -= 1
            k += step
        return y + k - 1

    def dome(self, cx, cz, r, y, b):
        """Half sphere. Returns the top y."""
        top = y
        for dy in range(int(math.ceil(r)) + 1):
            rr = math.sqrt(max(r * r - dy * dy, 0))
            if rr < 0.5 and dy > 0:
                break
            self.cylinder(cx, cz, rr, y + dy, y + dy + 1, b)
            top = y + dy
        return top

    def crenels(self, x0, x1, z0, z1, y, b, gx=0, gz=0):
        """Merlons on every second block of the outline (gx, gz: global offset for parity)."""
        for x in range(x0, x1):
            if (x + gx) % 2 == 0:
                self.set(x, y, z0, b); self.set(x, y, z1 - 1, b)
        for z in range(z0, z1):
            if (z + gz) % 2 == 0:
                self.set(x0, y, z, b); self.set(x1 - 1, y, z, b)

    def spire(self, x0, x1, z0, z1, y, b, steep=2, tip="lightning_rod"):
        """Tall pointed roof: the square gets smaller every `steep` blocks."""
        yy = y
        while x1 - x0 >= 1 and z1 - z0 >= 1:
            self.box(x0, x1, yy, yy + steep, z0, z1, b)
            yy += steep
            if x1 - x0 <= 1:
                break
            x0, x1, z0, z1 = x0 + 1, x1 - 1, z0 + 1, z1 - 1
        if tip:
            self.set((x0 + x1 - 1) // 2, yy, (z0 + z1 - 1) // 2, tip)
        return yy


# --------------------------------------------------------------------------------------------
# Building designs. Each function draws on canvas c with footprint width w.
# st = Style, col = player color name, T = blocks per tile, ctx = extra data (wall neighbours).
# --------------------------------------------------------------------------------------------
def inset(w):
    return 1 if w >= 7 else 0


def house(c, w, st, col, T, ctx):
    """Houses in four designs: cottage, front gable, two floors with an overhanging upper floor, cottage with shed."""
    rng = c.rng
    m = inset(w)
    pitched = st.shape in ("gable", "hip", "asian")
    kinds = ["cottage", "front_gable"] + (["jetty", "shed"] if w >= 8 else [])
    if not pitched:
        kinds = ["cottage"] + (["shed"] if w >= 8 else [])
    kind = kinds[int(rng.integers(len(kinds)))]
    x0, x1, z0, z1 = m, w - m, m, w - m
    if kind == "shed":
        x1 -= 2
    hw = 3 if w < 9 else 4
    mid = (x0 + x1) // 2
    if kind == "jetty":
        c.room(x0, x1, z0, z1 - 1, 0, 3, st.stone, st.floor, corner=st.timber)      # stone ground floor
        c.windows(x0, x1, z0, z1 - 1, 2, sides="ew")
        c.door(mid, 1, z1 - 2)
        c.timber_room(x0, x1, z0, z1, 3, 3, st, low_stone=0)                       # upper floor sticks out
        c.box(x0, x1, 2, 3, z1 - 1, z1, stair(family(st.wood.replace("_planks", ""))[0], "north", half="top"))
        c.windows(x0, x1, z0, z1, 5, sides="nsew", step=2)
        wall_top = 6
        axis = "x"
    else:
        c.timber_room(x0, x1, z0, z1, 0, hw, st)
        wall_top = hw
        axis = "z" if kind == "front_gable" else "x"
        c.windows(x0, x1, z0, z1, 2, sides="ew" if axis == "x" else "news")
        if axis == "x" and x1 - x0 >= 6:
            c.windows(x0, x1, z0, z1, 2, sides="s", step=4)
        c.box(mid - 1, mid + 2, 1, 3, z1, z1 + 1, -1)          # nothing in front of the door
        c.box(mid, mid + 1, 1, 3, z1 - 1, z1, st.plaster)
        c.door(mid, 1, z1 - 1)
    top = c.roof(x0, x1, z0, z1, wall_top + 1, st, axis=axis)
    if pitched and top > wall_top + 2:                                      # small window in the gable
        if axis == "z":
            c.set(mid, wall_top + 2, z1 - 1, "glass_pane")
        else:
            c.set(x0, wall_top + 2, (z0 + z1) // 2, "glass_pane")
    if kind == "shed":                                                     # open shed with firewood
        sx0, sx1 = x1, w - m
        for z in (z0, z1 - 1):
            c.box(sx1 - 1, sx1, 1, 3, z, z + 1, st.timber)
        c.box(sx0, sx1, 3, 4, z0, z1, family(st.roof)[1] + "[type=bottom]")
        c.box(sx0, sx1, 1, 3, z0 + 1, z1 - 1, "spruce_log[axis=z]" if rng.random() < 0.5 else "oak_log[axis=z]")
        c.box(sx0, sx1, 2, 3, z0 + 1 + (z1 - z0) // 2, z1 - 1, "air")
    # stone chimney with smoke on a random corner: only the European half-timbered houses have one in the game
    cx = x0 + 1 if rng.random() < 0.5 else x1 - 2
    cz = z0 + 1 if rng.random() < 0.6 else z1 - 2
    if kind == "jetty" or (cx, cz) == (mid, z1 - 2):                     # not in front of the door (shed)
        cz = z0 + 1
    if st.shape == "gable":
        c.box(cx, cx + 1, 1, top + 2, cz, cz + 1, st.stone2)
        c.set(cx, top + 2, cz, "campfire[lit=true,signal_fire=false]")
    if st.shape == "flat" and m and z1 - z0 > wall_top + 1:
        # flat roof terrace: an outside stair in the free margin (east, or west of a shed), and a cloth awning in
        # the player color over the door
        sx, rx = (x0 - 1, x0) if kind == "shed" else (x1, x1 - 1)
        for k in range(wall_top + 1):
            z = z1 - 1 - k
            c.box(sx, sx + 1, 1, 1 + k, z, z + 1, st.stone)
            c.set(sx, 1 + k, z, stair(family(st.roof)[0], "north"))
        c.set(rx, wall_top + 2, z1 - 1 - wall_top, "air")                 # a gap in the parapet
        c.box(mid - 1, mid + 2, 3, 4, z1, z1 + 1, f"{col}_wool")
    if kind == "jetty":
        furnish(c, x0 + 1, x1 - 1, z0 + 1, z1 - 2, 1, st, col, door=mid, bed=False)
        furnish(c, x0 + 1, x1 - 1, z0 + 1, z1 - 1, 4, st, col, table=False)
        c.banner(mid + 1, 1, z1 - 1, col)
    else:
        furnish(c, x0 + 1, x1 - 1, z0 + 1, z1 - 1, 1, st, col, door=mid)
        c.banner(mid + 1 if mid + 1 < x1 - 1 else mid - 1, 3 if wall_top > 3 else 2, z1, col)


def town_hall(c, x0, x1, z0, z1, y, door, st, col):
    """Furniture of the town center hall (#250): a long table with benches, the lectern of the town clerk at the
    back wall, chests and barrels, banners and a carpet in the player color, lanterns. Rooms x0..x1-1, z0..z1-1
    with the floor under y; the door is at x = door in the front wall (z = z1), so that column stays free."""
    wood = st.wood.replace("_planks", "")
    stairs, slab, _ = family(wood)
    mid = (z0 + z1) // 2
    tx = [x for x in range(x0 + 1, x1 - 1) if x != door]
    for x in tx:
        c.set(x, y, mid, f"{slab}[type=top]")
        c.set(x, y, mid - 1, stair(stairs, "north"))       # benches: the back faces away from the table
        c.set(x, y, mid + 1, stair(stairs, "south"))
    for x in tx[::2]:
        c.set(x, y + 1, mid, "lantern[hanging=false]")
    c.box(door, door + 1, y, y + 1, z0, z1, f"{col}_carpet")      # carpet from the door to the back wall
    c.set(door, y, z0, "lectern[facing=south]")
    c.set(x0, y, z0, "chest[facing=south]"); c.set(x1 - 1, y, z0, "barrel[facing=up]")
    c.set(x0, y, z1 - 1, "barrel[facing=up]")
    if x1 - 1 != door:
        c.set(x1 - 1, y, z1 - 1, "chest[facing=north]")
    for x in (x0 + 1, x1 - 2):
        c.banner(x, y + 2, z0, col)                              # on the back wall, facing the door
    c.set(x0, y + 2, mid, "wall_torch[facing=east]"); c.set(x1 - 1, y + 2, mid, "wall_torch[facing=west]")


def furnish(c, x0, x1, z0, z1, y, st, col, door=None, bed=True, table=True):
    """Furniture of a home in the room x0..x1-1, z0..z1-1 (inside the walls) on floor y: a bed in the player color
    along a side wall, a chest at the back wall, a table with a lantern and a stool, a rug. The door is in the south
    wall at x = door: the two cells inside it stay free."""
    rng = c.rng
    air = c.id("air")
    wood = st.wood.removesuffix("_planks")
    keep = {(door, z1 - 1), (door, z1 - 2)}
    free = lambda x, z: (x0 <= x < x1 and z0 <= z < z1 and (x, z) not in keep
                         and c.get(x, y, z) == air and c.get(x, y + 1, z) == air)
    sides = [x0, x1 - 1] if rng.random() < 0.5 else [x1 - 1, x0]
    if bed:
        for bx in sides:
            if free(bx, z0) and free(bx, z0 + 1):
                c.set(bx, y, z0, f"{col}_bed[facing=north,occupied=false,part=head]")
                c.set(bx, y, z0 + 1, f"{col}_bed[facing=north,occupied=false,part=foot]")
                break
    for x in sorted(range(x0, x1), key=lambda x: -abs(x - sides[0])):          # far from the bed
        if free(x, z0):
            c.set(x, y, z0, "chest[facing=south,type=single,waterlogged=false]")
            break
    if table:
        cells = [(x, z) for z in range(z0, z1) for x in range(x0, x1)]
        for i in rng.permutation(len(cells)):
            x, z = cells[i]
            side = next((d for d in (("east", 1, 0), ("west", -1, 0), ("south", 0, 1), ("north", 0, -1))
                         if free(x + d[1], z + d[2])), None)
            if free(x, z) and side:                                             # the stool turns its back away
                c.set(x, y, z, f"{wood}_slab[type=top,waterlogged=false]")
                c.set(x, y + 1, z, "lantern[hanging=false,waterlogged=false]")
                c.set(x + side[1], y, z + side[2], stair(f"{wood}_stairs", side[0]))
                break
    rug = ["red_carpet", "brown_carpet", "green_carpet", f"{col}_carpet"][int(rng.integers(4))]
    for x in range(x0 + 1, x1 - 1):
        for z in range(z0 + 1, z1 - 1):
            if c.get(x, y, z) == air:
                c.set(x, y, z, rug)


def town_center(c, w, st, col, T, ctx):
    """The in-game model: a high main building at the back (open ground floor on posts, the hall above it,
    stairs up at the front) and two L-shaped open sheds on posts at the front corners around an open yard."""
    c.box(0, w, 0, 1, 0, w, st.stone2)
    a = max(1, w // 4)                               # width of the sheds
    ph = 4 if w >= 8 else 3                          # height of the open ground floor
    mid = w // 2
    hx0, hx1, hz0 = a, w - a, 1
    hz1 = min(hz0 + hx1 - hx0, w - a)
    # Sheds: posts on the outer edges, a roof in the style of the set, open to the yard.
    for x0, x1 in ((0, a), (w - a, w)):
        fx0, fx1 = (0, max(a, mid - 2)) if x0 == 0 else (min(w - a, mid + 2), w)
        for ax0, ax1, az0, az1, axis in ((x0, x1, hz0 + 2, w, "z"), (fx0, fx1, w - a, w, "x")):
            for x in sorted({ax0, ax1 - 1, *range(ax0, ax1, 3)}):
                for z in sorted({az0, az1 - 1, *range(az0, az1, 3)}):
                    if x in (0, w - 1) or z == w - 1 or (x, z) in ((ax0, az0), (ax1 - 1, az0)):
                        c.box(x, x + 1, 1, ph, z, z + 1, st.timber)
            if st.shape == "flat":                  # flat roof with a trim (MENA: arcades with a blue band)
                c.flat_roof(ax0, ax1, az0, az1, ph, st.roof)
                c.walls(ax0, ax1, ph - 1, ph, az0, az1, st.accent)
            else:
                c.roof(ax0, ax1, az0, az1, ph, st, fill_block=-1, axis=axis, over=0)
        c.set(x0 + (1 if x0 == 0 else a - 2), 1, w - 2, "barrel[facing=up]")
        c.set(fx0 + 1 if x0 == 0 else fx1 - 2, 1, w - 2, "hay_block")
    # Main building: the hall stands on posts; a band in the player color at the floor line.
    hp, hh = (ph + 1, 6) if w >= 8 else (ph, 3)     # floor and wall height of the hall
    c.upper = hp                                     # the garrison stands in the hall, where the player sees it (#2054)
    for x in sorted({hx0, hx1 - 1, *range(hx0, hx1, 3)}):
        for z in sorted({hz0, hz1 - 1, *range(hz0, hz1, 3)}):
            c.box(x, x + 1, 1, hp, z, z + 1, st.timber)
    c.timber_room(hx0, hx1, hz0, hz1, hp, hh, st, low_stone=0)
    c.walls(hx0, hx1, hp, hp + 1, hz0, hz1, f"{col}_wool")
    c.windows(hx0, hx1, hz0, hz1, hp + 2, step=3)
    top = c.roof(hx0, hx1, hz0, hz1, hp + hh + 1, st, axis="x")
    if st.shape == "gable" and hx1 - hx0 >= 6:      # cross gable over the front
        g0, g1 = hx0 + 1, hx1 - 1
        top = max(top, c.gable(g0 - 1, g1 + 1, (hz0 + hz1) // 2, hz1 + 1, hp + hh, st.roof,
                               fill=(g0, g1, hz0, hz1, st.plaster), axis="z"))
    if st.domes:
        top = c.dome((hx0 + hx1 - 1) / 2, (hz0 + hz1 - 1) / 2, (hx1 - hx0) / 2 - 1, top, st.dome)
    # Stairs from the yard up to the door of the hall.
    sx = min(mid + 1, hx1 - 2)
    for i in range(hp):
        c.set(sx, 1 + i, hz1 + hp - 1 - i, stair(family(st.wood.replace("_planks", ""))[0], "north"))
    c.door(sx, hp + 1, hz1 - 1)
    c.set(mid - 1, hp - 1, hz1 - 2, "bell[attachment=ceiling,facing=south]")       # the town bell
    c.set(hx0 + 1, 1, hz1 - 2, "barrel[facing=up]"); c.set(hx1 - 2, 1, hz0 + 1, "chest[facing=south]")
    if hx1 - hx0 >= 6 and hz1 - hz0 >= 6:
        town_hall(c, hx0 + 1, hx1 - 1, hz0 + 1, hz1 - 1, hp + 1, sx, st, col)
    for x in (hx0 + 1, hx1 - 2):
        if x != sx:
            c.banner(x, hp + 3, hz1, col)
    c.flag(mid, top + 1, (hz0 + hz1) // 2, col, 2)


COPPER = {"lantern": "waxed_copper_lantern", "iron_chain": "waxed_copper_chain", "iron_bars": "waxed_copper_bars"}


def castle(c, w, st, col, T, ctx, small=False):
    stone = st.stone
    th = 2 if w >= 14 else 1                         # wall thickness
    hw = max(5, round(w * 0.38))                     # curtain wall height
    c.box(0, w, 0, 1, 0, w, st.stone2)
    c.box(2, w - 2, 0, 1, 2, w - 2, "gravel" if st.framing == "timber" else st.floor)
    c.walls(1, w - 1, 1, hw + 1, 1, w - 1, stone, t=th)
    if st.framing == "bands":
        c.walls(1, w - 1, 1, 2, 1, w - 1, st.accent)                     # base row
    c.walls(1, w - 1, hw, hw + 1, 1, w - 1, f"{col}_wool")               # player band under the merlons
    c.crenels(1, w - 1, 1, w - 1, hw + 1, (st.merlon or stone))
    roofed = st.shape in ("gable", "hip", "asian")
    asian = st.shape == "asian"
    roof = family(st.roof)[2] if roofed else None
    # Round corner towers that stand out from the walls
    r = max(1.6, w / 7)
    for cx in (r - 0.5, w - r - 0.5):
        for cz in (r - 0.5, w - r - 0.5):
            c.cylinder(cx, cz, r, 1, hw + 4, stone)
            c.cylinder(cx, cz, r - 1, hw + 1, hw + 4, "air")
            c.cylinder(cx, cz, r, hw + 2, hw + 3, f"{col}_wool", hollow=True)
            c.cylinder(cx, cz, r - 1, hw + 3, hw + 4, st.wood)
            for y in range(3, hw + 2, 3):
                ix, iz = int(round(cx)), int(round(cz))
                if cz > w / 2:
                    c.set(ix, y, int(round(cz + r - 0.5)), "iron_bars")
                else:
                    c.set(int(round(cx + r - 0.5)), y, iz, "iron_bars")
            if asian:                   # square roofs with upturned corners
                c.hip(int(cx - r) - 1, int(cx + r) + 2, int(cz - r) - 1, int(cz + r) + 2, hw + 4, st.roof, flare=True)
            elif roofed:
                c.cone(cx, cz, r + 0.5, hw + 4, roof)
            else:
                c.cylinder(cx, cz, r, hw + 4, hw + 5, stone)
                c.cylinder(cx, cz, r - 1, hw + 4, hw + 5, "air")
    # Gatehouse in the middle of the south wall
    mid = w // 2
    gw = 3 if w >= 12 else 2
    g0 = mid - gw // 2
    gz0 = w - 2 - th
    c.box(g0 - 2, g0 + gw + 2, 1, hw + 3, gz0, w, stone)
    c.crenels(g0 - 2, g0 + gw + 2, gz0, w, hw + 3, (st.merlon or stone))
    c.box(g0 - 1, g0 + gw + 1, hw + 2, hw + 3, gz0 + 1, w - 1, st.wood)
    c.box(g0, g0 + gw, 1, 5, gz0, w, "air")
    c.box(g0, g0 + gw, 4, 5, w - 1, w, "iron_bars")
    c.banner(g0 - 2, hw, w, col); c.banner(g0 + gw + 1, hw, w, col)
    # Keep: tall square tower with corner turrets
    k = max(3, w // 4)
    kh = max(hw + 5, round(w * 0.85))
    c.room(k, w - k, k, w - k, 0, kh, stone, st.floor)
    for y in range(hw, kh, 4):
        c.box(k + 1, w - k - 1, y, y + 1, k + 1, w - k - 1, st.wood)        # floors
    c.box(k + 1, w - k - 1, kh, kh + 1, k + 1, w - k - 1, st.wood)
    c.crenels(k, w - k, k, w - k, kh + 1, (st.merlon or stone))
    for y in (hw + 2, kh - 2):
        c.windows(k, w - k, k, w - k, y, b=COPPER["iron_bars"], step=2, height=2)
    c.box(mid - (gw // 2), mid - (gw // 2) + gw, 1, 4, w - k - 1, w - k, "air")
    if w - 2 * k >= 5:
        keep_inside(c, k + 1, w - k - 1, [0, *range(hw, kh, 4)], kh, st, col)
    if asian:
        # Tenshu: white plastered upper floors on the stone base, a flared roof skirt at each floor
        c.walls(k, w - k, hw + 1, kh + 1, k, w - k, st.plaster)
        for x in (k, w - k - 1):
            for z in (k, w - k - 1):
                c.box(x, x + 1, hw + 1, kh + 1, z, z + 1, st.timber)
        c.windows(k, w - k, k, w - k, kh - 2, b=COPPER["iron_bars"], step=2, height=2)
        for y in range(hw + 1, kh - 1, 4):
            c.hip(k - 1, w - k + 1, k - 1, w - k + 1, y, st.roof, layers=1, flare=True)
        top = c.hip(k - 1, w - k + 1, k - 1, w - k + 1, kh + 1, st.roof, flare=True)
        for x in range(k + 1, w - k - 1, 3):
            c.banner(x, hw - 1, w - k, col)
        c.flag(mid, top + 1, mid, col, 3)
        return
    domed = st.torons or st.dome == "bricks"          # Malian and Byzantine castles: a dome on the keep
    for tx in (k, w - k - 2):
        for tz in (k, w - k - 2):
            c.box(tx, tx + 2, kh + 1, kh + 4, tz, tz + 2, stone)
            if roofed and not domed:
                c.spire(tx - 1, tx + 3, tz - 1, tz + 3, kh + 4, roof, steep=1, tip=None)
            else:
                c.crenels(tx, tx + 2, tz, tz + 2, kh + 4, (st.merlon or stone))
    for x in range(k + 1, w - k - 1, 3):
        c.banner(x, kh - 3, w - k, col)
    if domed:
        rd = (w - 2 * k) / 2 - 1
        c.cylinder(mid - 0.5, mid - 0.5, rd, kh + 1, kh + 3, st.accent)              # drum
        top = c.dome(mid - 0.5, mid - 0.5, rd, kh + 3, st.dome)
        c.flag(mid, top + 1, mid, col, 3)
        return
    c.flag(mid, kh + 1, mid, col, 5)


def keep_inside(c, x0, x1, floors, top, st, col, z0=None, z1=None):
    """Furniture of a keep with the inside x0..x1-1, z0..z1-1 (default: as x) and floor blocks at the y of
    `floors` (#256): a throne room on the ground floor, then storage and an armory. A ladder on the east wall
    joins the floors."""
    z0, z1 = (x0, x1) if z0 is None else (z0, z1)
    wood = st.wood.removesuffix("_planks")
    wood = wood if wood in WOODS else "spruce"
    mid, mz = (x0 + x1) // 2, (z0 + z1) // 2
    for i, f in enumerate(floors):
        y = f + 1
        ceil = floors[i + 1] if i + 1 < len(floors) else top
        if i == 0:                                       # throne room: throne, carpet from the door, banners
            c.set(mid, y, z0, stair(f"{wood}_stairs", "north"))
            c.box(mid, mid + 1, y, y + 1, z0 + 1, z1, f"{col}_carpet")
            c.banner(x0, y + 2, z0, col); c.banner(x1 - 1, y + 2, z0, col)
        elif i % 2:                                      # storage
            c.set(x0, y, z0, "chest[facing=east]")
            c.box(x0, x0 + 1, y, y + 1, z0 + 1, z1 - 1, "barrel[facing=up]")
        else:                                            # armory and study
            c.set(x0, y, z0, "grindstone[face=floor,facing=east]")
            c.set(x0, y, z0 + 1, "smithing_table")
            c.set(x0, y, z1 - 1, "lectern[facing=east,has_book=true,powered=false]")
        c.set(mid, ceil - 1, mz, "lantern[hanging=true]")
        if i:
            c.set(x0, y, mz, "lantern[hanging=false]")
    c.box(x1 - 1, x1, 1, top, z0 + 1, z0 + 2, "ladder[facing=west]")   # through the floors, not the roof


def krepost(c, w, st, col, T, ctx):
    """Bulgarian Krepost (#122): a tall square keep at the back, a round tower with a cone roof (west), a gatehouse
    with an open arch (front) and a tower with a hip roof (east), wooden hoardings between them. The game has one
    model for all sets: brick walls on a stone base and red tile roofs."""
    s = w / 12                                                            # the design is drawn for 3 tiles
    S = lambda v: round(v * s)
    base, wall, roof = st.stone2, "bricks", "red_sandstone"             # red_sandstone: the orange roof tiles
    c.box(0, w, 0, 1, 0, w, base)
    def block(x0, x1, z0, z1, h):                                         # stone up to 3, brick above
        c.box(x0, x1, 1, h, z0, z1, wall)
        c.box(x0, x1, 1, min(h, 4), z0, z1, "stone_bricks")
    # Keep: the highest part, with merlons and a band in the player color
    kx0, kx1, kz0, kz1, kh = S(4), w - 1, S(1), S(7), S(17)
    block(kx0, kx1, kz0, kz1, kh)
    c.walls(kx0 - 1, kx1 + 1, kh, kh + 1, kz0 - 1, kz1 + 1, wall)       # machicolation ledge
    c.walls(kx0 - 1, kx1 + 1, kh - 1, kh, kz0 - 1, kz1 + 1, f"{col}_wool")
    c.box(kx0, kx1, kh, kh + 1, kz0, kz1, "bricks")
    c.crenels(kx0 - 1, kx1 + 1, kz0 - 1, kz1 + 1, kh + 1, wall)
    for y in (kh - 8, kh - 4):                                            # narrow windows
        for x in range(kx0 + 1, kx1 - 1, 2):
            c.set(x, y, kz0, "iron_bars"); c.set(x, y, kz1 - 1, "iron_bars")
        for z in range(kz0 + 1, kz1 - 1, 2):
            c.set(kx1 - 1, y, z, "iron_bars"); c.set(kx0, y, z, "iron_bars")
    c.flag((kx0 + kx1) // 2, kh + 1, (kz0 + kz1) // 2, col, 3)
    if kx1 - kx0 >= 6 and kz1 - kz0 >= 5:                                 # hollow keep with 3 floors (#330)
        c.box(kx0 + 1, kx1 - 1, 1, kh, kz0 + 1, kz1 - 1, "air")
        floors = [0, kh - 11, kh - 6]                                     # under the windows at kh - 8 and kh - 4
        for f in floors[1:]:
            c.box(kx0 + 1, kx1 - 1, f, f + 1, kz0 + 1, kz1 - 1, st.wood)
        keep_inside(c, kx0 + 1, kx1 - 1, floors, kh, st, col, kz0 + 1, kz1 - 1)
    # Round tower in the west with a cone roof
    r, cx, cz, rh = 2.3 * s, S(2.5), S(3.5), S(11)
    c.cylinder(cx, cz, r, 1, rh, wall)
    c.cylinder(cx, cz, r, 1, 4, "stone_bricks")
    c.cylinder(cx, cz, r + 0.6, rh - 1, rh, "stone_bricks")              # cornice
    for y in (S(6), rh - 2):
        c.set(int(cx + r), y, int(cz), "iron_bars"); c.set(int(cx), y, int(cz + r), "iron_bars")
    c.cone(cx, cz, r + 1, rh, "red_sandstone")
    c.set(int(cx), rh + int(r + 1), int(cz), "lightning_rod")
    # Gatehouse at the front with an open arch and a gable roof
    gx0, gx1, gz0, gh = 0, S(5), S(7), S(6)
    block(gx0, gx1, gz0, w, gh)
    mid = (gx0 + gx1) // 2
    c.box(mid - 1, mid + 1, 1, 4, gz0, w, "air")                         # passage through the gatehouse
    c.box(mid - 1, mid + 1, 4, 5, w - 1, w, "stone_bricks")              # arch stones
    c.box(mid - 1, mid + 1, 3, 4, w - 1, w, "iron_bars")                 # raised portcullis
    c.gable(gx0 - 1, gx1 + 1, gz0, w + 1, gh, roof, fill=(gx0, gx1, gz0, w, wall), axis="z")
    # Tower in the east with a hip roof and banners
    ex0, ez0, eh = S(7), S(7), S(10)
    block(ex0, w, ez0, w, eh)
    for x in range(ex0 + 1, w - 1, 2):
        c.set(x, eh - 3, w - 1, "iron_bars")
        c.banner(x, eh - 5, w, col)
    c.hip(ex0 - 1, w + 1, ez0 - 1, w + 1, eh, roof)
    c.box(gx1, ex0, 1, S(8), kz1, w - 1, wall)                           # wall between gatehouse and east tower
    c.box(gx1, ex0, 1, 4, kz1, w - 1, "stone_bricks")
    # Wooden hoarding on the front of the keep, above the roofs
    hy = S(13)
    c.box(kx0, kx1, hy, hy + 1, kz1, kz1 + 1, "spruce_planks")
    c.box(kx0, kx1, hy + 1, hy + 2, kz1, kz1 + 1, "spruce_fence")
    for x in (kx0, kx1 - 1):
        c.set(x, hy + 2, kz1, "spruce_fence")


def hall_with_yard(c, w, st, col, depth=0.6, hw=4, open_front=False):
    """Long hall on the north side and a yard on the south side. Returns (hall z1, hall top y)."""
    m = 1 if w >= 8 else 0
    hz = max(4, round(w * depth))
    x0, x1, z0, z1 = m, w - m, m, hz
    if open_front:
        c.box(x0, x1, 0, 1, z0, z1, st.floor)
        c.walls(x0, x1, 1, hw + 1, z0, z1, st.plaster)
        c.box(x0 + 1, x1 - 1, 1, hw + 1, z1 - 1, z1, "air")
        c.box(x0 + 1, x1 - 1, 1, hw + 1, z0 + 1, z1 - 1, "air")
        for x in range(x0, x1, 3):
            c.box(x, x + 1, 1, hw + 1, z1 - 1, z1, st.timber)
        c.box(x1 - 1, x1, 1, hw + 1, z1 - 1, z1, st.timber)
        c.box(x0, x1, hw + 1, hw + 2, z1 - 1, z1, st.beam + "[axis=x]")
        c.box(x0, x0 + 1, 1, hw + 1, z0, z0 + 1, st.timber); c.box(x1 - 1, x1, 1, hw + 1, z0, z0 + 1, st.timber)
    else:
        c.timber_room(x0, x1, z0, z1, 0, hw, st, low_stone=1)
        c.windows(x0, x1, z0, z1, 2, sides="news")
    top = c.roof(x0, x1, z0, z1, hw + 1 + (1 if open_front else 0), st, axis="x")
    # Yard with a fence
    c.box(0, w, 0, 1, z1, w, "coarse_dirt")
    c.box(0, 1, 1, 2, z1, w, "oak_fence"); c.box(w - 1, w, 1, 2, z1, w, "oak_fence")
    c.box(0, w, 1, 2, w - 1, w, "oak_fence")
    c.box(w // 2 - 1, w // 2 + 1, 1, 2, w - 1, w, "air")
    return z1, top


def barracks(c, w, st, col, T, ctx):
    """Western model: a stone ground floor with a timber upper floor and a gable roof, and a yard with a low
    stone wall in front (training dummies, a grindstone)."""
    if w < 8:
        z1, top = hall_with_yard(c, w, st, col)
        c.door(w // 2, 1, z1 - 1)
        c.flag(1, top - 1, z1 - 2, col, 3)
        return
    x0, x1, z0, z1 = 1, w - 1, 1, max(5, round(w * 0.55))
    mid = w // 2
    c.room(x0, x1, z0, z1, 0, 3, st.stone, st.floor)                       # stone ground floor
    c.timber_room(x0, x1, z0, z1, 3, 4, st, low_stone=0)                   # timber upper floor
    c.windows(x0, x1, z0, z1, 2, b="iron_bars", sides="ew")
    c.windows(x0, x1, z0, z1, 5, sides="news")
    top = c.roof(x0, x1, z0, z1, 8, st, axis="x")
    c.door(mid, 1, z1 - 1)
    c.banner(mid + 1, 3, z1, col); c.banner(mid - 2, 3, z1, col)
    # Yard: a low stone wall with a gate opening in the middle of the south side
    c.box(0, w, 0, 1, z1, w, st.stone2)
    c.walls(0, w, 1, 2, z1 - 1, w, st.stone)
    c.box(1, w - 1, 1, 2, z1, w - 1, "air")
    c.box(0, w, 2, 3, w - 1, w, st.accent_wall); c.box(0, 1, 2, 3, z1, w, st.accent_wall)
    c.box(w - 1, w, 2, 3, z1, w, st.accent_wall)
    c.box(mid - 1, mid + 1, 1, 3, w - 1, w, "air")
    for x in (2, w - 3):                              # training dummies
        if z1 + 1 < w - 2:
            c.set(x, 1, z1 + 1, "oak_fence"); c.set(x, 2, z1 + 1, "hay_block")
            c.set(x, 3, z1 + 1, "carved_pumpkin[facing=south]")
    c.set(w - 3, 1, w - 2, "grindstone[face=floor,facing=south]")
    c.flag(x0 + 1, top - 1, (z0 + z1) // 2, col, 3)
    # Inside: straw bunks (#541), weapon racks (grindstones), chests, lanterns, a ladder to the upper floor
    ix0, ix1, iz0, iz1 = x0 + 1, x1 - 2, z0 + 1, z1 - 2                  # the free inside, inclusive
    if ix1 - ix0 < 7 or iz1 - iz0 < 3:
        for x in range(ix0, ix1 + 1, 2):
            c.bed(x, 1, iz0, "straw")
        c.set(ix1, 4, iz0, "lantern[hanging=false]")
        return
    for x in (ix0, ix0 + 1, ix1 - 1, ix1):
        c.bed(x, 1, iz0, "straw")
    c.set(mid - 1, 1, iz0, "grindstone[face=floor,facing=south]"); c.set(mid + 1, 1, iz0, "grindstone[face=floor,facing=south]")
    c.set(mid, 1, iz0, "chest[facing=south,type=single,waterlogged=false]")
    c.set(ix0, 1, iz1, "barrel[facing=up,open=false]")
    for x in (ix0 + 2, ix1 - 2):
        c.set(x, 2, iz0 + 2, "lantern[hanging=true]")
    c.box(ix1, ix1 + 1, 1, 4, iz1, iz1 + 1, "ladder[facing=west]")         # through a hole in the upper floor
    for x in range(ix0, ix1, 2):
        c.bed(x, 4, iz0, "straw")
    for x in range(ix0, ix1 - 1, 2):
        c.bed(x, 4, iz1, "straw", "south")
    c.set(ix1, 4, iz0, "lantern[hanging=false]")


def archery_range(c, w, st, col, T, ctx):
    """Western model: a long open shed, a round tower on the west end and a row of targets in front."""
    z1, top = hall_with_yard(c, w, st, col, depth=0.5, hw=3, open_front=True)
    for x in range(2, w - 2, 3):                      # targets at the south side
        c.set(x, 1, w - 2, "hay_block"); c.set(x, 2, w - 2, "target")
    c.set(w - 2, 1, 2, "fletching_table")
    c.banner(w // 2, 4, z1, col)
    # Inside: barrels and a chest of arrows and bows, a bench that looks at the targets, torches on the back wall
    ix1 = w - 3                                       # the last free x inside the hall
    ix0 = max(2, ix1 - 4) if w >= 10 else 2           # east of the tower
    c.set(ix0, 1, 2, "barrel[facing=up,open=false]"); c.set(ix0 + 1, 1, 2, "barrel[facing=up,open=false]")
    c.set(ix1, 1, 2, "chest[facing=south,type=single,waterlogged=false]")
    if z1 - 2 > 2:
        c.set(ix0, 1, z1 - 2, "barrel[facing=up,open=false]")
        for x in range(ix0 + 2, ix1):
            c.set(x, 1, 3, "spruce_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]")
    for x in (ix0, ix1):
        c.set(x, 3, 2, "wall_torch[facing=south]")
    if w < 10:
        return
    r = 2                                             # round tower with a pointed roof
    cx = cz = r + 0.5
    th = top + 2
    c.cylinder(cx, cz, r, 1, th, st.plaster)
    c.cylinder(cx, cz, r, 1, 3, st.stone)
    c.cylinder(cx, cz, r - 1, 1, th, "air")
    c.box(int(cx) - 1, int(cx) + 2, th - 1, th, int(cz) - 1, int(cz) + 2, st.wood)
    for y in (4, th - 2):
        c.set(int(cx), y, int(cz + r), "glass_pane"); c.set(int(cx + r), y, int(cz), "glass_pane")
    if st.shape == "flat":
        c.cylinder(cx, cz, r, th, th + 1, st.accent_wall)
        c.cylinder(cx, cz, r - 1, th, th + 1, "air")
    else:
        c.cone(cx, cz, r + 1, th, family(st.roof)[2])
    c.flag(int(cx), th + (1 if st.shape == "flat" else 3), int(cz), col, 2)


def stable(c, w, st, col, T, ctx):
    """Western model: a timber barn with a gable roof and a long lean-to over the horse stalls on the south
    side (hay, a water trough)."""
    m = 1 if w >= 8 else 0
    hz = max(4, round(w * 0.55)) if w >= 8 else max(3, w - 2)
    x0, x1, z0, z1 = m, w - m, m, hz
    hw = 6 if w >= 8 else 4
    c.timber_room(x0, x1, z0, z1, 0, hw, st)
    c.windows(x0, x1, z0, z1, 4, sides="ew")
    c.roof(x0, x1, z0, z1, hw + 1, st, fill_block=st.wood, axis="x")
    mid = w // 2
    c.box(mid - 1, mid + 1, 1, 4, z1 - 1, z1, "air")                       # barn door to the stalls
    for x in range(x0 + 1, x1 - 1, 2):
        c.set(x, 1, z0 + 1, "hay_block")
    if w < 8:
        c.banner(mid - 1, 3, z1, col)
        return
    # Lean-to: posts on the front, a roof that slopes down to the south, stalls with fence dividers
    stairs = family(st.roof)[0] if st.shape != "flat" else family(st.roof)[1]
    for z in range(z1 + 1, w):                                             # z1: the eave of the barn roof
        y = hw - 1 - (z - z1 - 1) // 2
        b = stair(stairs, "north") if st.shape != "flat" else f"{stairs}[type=bottom]"
        c.box(x0, x1, max(y, 4), max(y, 4) + 1, z, z + 1, b)
    c.box(x0, x1, 0, 1, z1, w, st.floor)
    for x in list(range(x0, x1 - 1, 3)) + [x1 - 1]:
        c.box(x, x + 1, 1, 4, w - 1, w, st.timber)
        if x0 < x < x1 - 1:
            c.box(x, x + 1, 1, 2, z1, w - 2, "oak_fence")                   # stall dividers
    for x in range(x0 + 1, x1 - 1, 3):
        c.set(x, 1, z1, "hay_block")
    c.banner(mid - 2, hw - 1, z1, col)
    c.set(w - 1, 1, w - 2, "water_cauldron[level=3]")                     # water trough
    # Inside: stalls with fence dividers and troughs under a hay loft, a chest for the saddles, torches
    ix0, ix1, iz0, iz1 = x0 + 1, x1 - 2, z0 + 1, z1 - 2                  # the free inside, inclusive
    if iz1 - iz0 < 3:
        return
    c.box(ix0, ix1 + 1, 3, 4, iz0, iz0 + 2, "spruce_slab[type=top,waterlogged=false]")        # the loft
    for x in range(ix0 + 1, ix1, 2):
        c.box(x, x + 1, 1, 2, iz0, iz0 + 3, "oak_fence")                   # stall dividers
        if x + 1 < ix1:
            c.set(x + 1, 1, iz0 + 1, "water_cauldron[level=3]")
    for x in range(ix0, ix1 + 1):
        if (x - ix0) % 3 != 2:
            c.set(x, 4, iz0, "hay_block")
    c.set(ix0, 5, iz0, "hay_block"); c.set(ix1, 5, iz0, "hay_block")
    c.set(ix0, 1, iz1, "chest[facing=east,type=single,waterlogged=false]")
    c.set(ix1, 1, iz1, "barrel[facing=up,open=false]")
    c.set(ix0, 2, iz1 - 1, "wall_torch[facing=east]"); c.set(ix1, 2, iz1 - 1, "wall_torch[facing=west]")


def siege_workshop(c, w, st, col, T, ctx):
    hx = w // 2 + 1
    c.box(0, w, 0, 1, 0, w, "coarse_dirt")
    c.timber_room(1, hx, 1, w - 1, 0, 5, st, low_stone=1)
    c.windows(1, hx, 1, w - 1, 3, sides="nsw")
    c.roof(1, hx, 1, w - 1, 6, st, axis="z")
    c.box(hx - 1, hx, 1, 5, w // 2 - 1, w // 2 + 2, "air")                 # wide door to the yard
    # Inside (x 2..hx-2, z 2..w-3): a ram on wheels in the making, a carpenter bench, planks and pitch
    a, b, zb = 2, hx - 2, w - 3
    if b - a >= 3:
        rz0, rz1 = 3, max(5, w // 2 - 2)                                   # the ram stays out of the door path
        for x in (a + 1, b - 1):
            c.box(x, x + 1, 1, 2, rz0, rz1 + 1, "stripped_spruce_log[axis=z]")
            for z, f in ((rz0, "north"), (rz1, "south")):                  # an axle with a wheel on each side
                c.set(x + (-1 if x == a + 1 else 1), 1, z, f"spruce_trapdoor[facing={'west' if x == a + 1 else 'east'},half=bottom,open=true]")
        c.box(a + 2, b - 1, 2, 3, rz0, rz0 + 1, "oak_fence")
        c.box(a + 2, b - 1, 2, 3, rz1, rz1 + 1, "oak_fence")
        c.box((a + b) // 2, (a + b) // 2 + 1, 3, 4, rz0 - 1, rz1 + 2, "stripped_oak_log[axis=z]")    # the ram beam
        c.set((a + b) // 2, 3, rz0 - 1, "iron_block")                      # its iron head
        hang(c, (a + b) // 2, 5, rz1)
        c.set(a, 1, zb - 2, "crafting_table")                              # the carpenter bench at the west wall
        c.set(a, 1, zb - 1, "smithing_table")
        c.set(a, 1, zb, "grindstone[face=floor,facing=north]")
        c.box(b - 1, b + 1, 1, 2, zb - 1, zb + 1, st.wood)                 # a stack of planks
        c.box(b - 1, b + 1, 2, 3, zb, zb + 1, "spruce_slab[type=bottom]")
        c.set(b, 1, a, "barrel[facing=up]")                                # barrels of pitch
        c.set(b, 2, a, "barrel[facing=up]")
        c.set(b - 1, 1, a, "barrel[facing=north]")
        hang(c, a + 1, 4, zb - 1)
    # Crane: an A-frame with a chain
    ch = max(7, round(w * 0.6))
    cx = w - 3
    for z in (2, w - 3):
        c.box(cx, cx + 1, 1, ch, z, z + 1, st.timber)
    c.box(cx, cx + 1, ch, ch + 1, 2, w - 2, st.beam + "[axis=z]")
    c.box(cx, cx + 1, ch - 3, ch, w // 2, w // 2 + 1, "iron_chain")
    c.set(cx, ch - 4, w // 2, "oak_log[axis=x]")
    c.box(hx + 1, hx + 3, 1, 2, w - 3, w - 1, "oak_log[axis=x]")           # timber pile
    # A siege engine under construction in the yard: a wooden frame with a ram beam, and barrels at the hall
    rx, rz = hx + 1, 3
    c.box(rx, rx + 3, 1, 2, rz, rz + 2, "spruce_slab[type=bottom]")
    for x in (rx, rx + 2):
        for z in (rz, rz + 1):
            c.set(x, 2, z, "oak_fence")
    c.box(rx, rx + 3, 3, 4, rz, rz + 2, "spruce_slab[type=bottom]")
    c.set(rx + 1, 2, rz, "oak_log[axis=x]"); c.set(rx + 1, 2, rz + 1, "oak_log[axis=x]")
    c.set(hx, 1, 2, "barrel[facing=up]"); c.set(hx, 1, 3, "barrel[facing=up]"); c.set(hx, 2, 2, "barrel[facing=up]")
    c.set(hx + 1, 2, w - 2, "oak_log[axis=x]")
    c.banner(hx // 2 + 1, 4, w - 1, col)
    c.flag(cx, ch + 1, 2, col, 2)


def blacksmith(c, w, st, col, T, ctx):
    m = 1
    hz = w - 3
    c.box(0, w, 0, 1, 0, w, st.stone2)
    c.timber_room(m, w - m, m, hz, 0, 4, st, low_stone=2)
    c.windows(m, w - m, m, hz, 3, sides="new")
    top = c.roof(m, w - m, m, hz, 5, st, axis="x")
    c.box(w - m - 2, w - m, 1, top + 2, m + 1, m + 3, st.stone2)            # forge chimney of rough stone, as in the game
    c.set(w - m - 2, top + 2, m + 1, "campfire[lit=true,signal_fire=false]")
    c.set(w - m - 2, 1, m + 3, "blast_furnace[facing=south,lit=true]")
    mid = w // 2
    c.door(mid - 1, 1, hz - 1)
    # Porch with tools
    for x in (m, w - m - 1):
        c.box(x, x + 1, 1, 4, w - 1, w, st.timber)
    if st.shape != "flat":
        c.box(m, w - m, 4, 5, hz, w, stair(family(st.roof)[0], "north"))
    else:
        c.box(m, w - m, 4, 5, hz, w, family(st.roof)[1] + "[type=bottom]")
    c.set(mid + 1, 1, hz + 1, "anvil[facing=east]")
    c.set(mid + 2, 1, hz, "smithing_table"); c.set(m + 1, 1, hz, "water_cauldron[level=3]")
    c.set(w - m - 2, 1, hz + 1, "grindstone[face=floor,facing=east]")      # the workshop in front: tools and stock
    c.set(m + 1, 1, hz + 1, "barrel[facing=up]")
    c.set(mid + 1, 3, hz + 1, "lantern[hanging=true]")
    c.banner(mid + 1, 3, hz, col)
    # The smithy inside: the hearth at the chimney, anvils, the quench tub, tools and stock along the walls
    e, n = w - m - 3, m + 1                                                # east of the room (beside the chimney), north wall
    c.furniture([(e, 1, n, "lava_cauldron"), (e - 1, 1, n, "water_cauldron[level=3]"), (e - 1, 1, n + 2, "anvil[facing=east]"),
               (m + 1, 1, n, "grindstone[face=floor,facing=north]"), (m + 2, 1, n, "smithing_table"),
               (m + 3, 1, n, "barrel[facing=up]"), (m + 3, 2, n, "barrel[facing=up]"), (m + 4, 1, n, "chest[facing=south]"),
               (m + 1, 1, n + 2, "chipped_anvil[facing=north]"), (m + 1, 1, n + 4, "chest[facing=east]"),
               (m + 1, 1, n + 5, "barrel[facing=up]"), (m + 1, 4, n + 2, "iron_chain"), (e, 4, n + 4, "iron_chain"),
               (m + 1, 3, n + 2, "lantern[hanging=true]"), (e, 3, n + 4, "lantern[hanging=true]")])
    wood = st.wood.replace("_planks", "")
    shelf = f"{wood if wood in WOODS else 'spruce'}_shelf[facing=south,powered=false,side_chain=unconnected]"
    c.furniture([(x, 2, n, shelf) for x in (m + 1, m + 2, m + 4)])        # tools on shelves over the bench (#526)
    c.goods = ("iron_sword", "iron_axe", "iron_pickaxe", "iron_shovel", "iron_hoe", "shears", "iron_ingot",
               "iron_helmet", "iron_horse_armor", "shield", "iron_nugget", "bucket")


def market(c, w, st, col, T, ctx):
    """Market: a two-floor hall at the back, a paved yard with a trading table, and lean-to stalls around it."""
    c.box(0, w, 0, 1, 0, w, st.stone2)
    d = max(4, w * 3 // 8)                                                 # depth of the hall
    h = 7 if w >= 12 else 5
    c.timber_room(1, w - 1, 0, d, 0, h, st, low_stone=1)
    c.windows(1, w - 1, 0, d, 2, step=3)
    c.windows(1, w - 1, 0, d, h - 2, step=3)
    top = c.roof(1, w - 1, 0, d, h + 1, st, axis="x")
    c.door(w // 2, 1, d - 1)
    c.banner(w // 2 - 1, 3, d, col); c.banner(w // 2 + 1, 3, d, col)
    # The hall inside: shelves of goods on the back wall, a counter with the ledger, a store room upstairs
    wood = st.wood.replace("_planks", "")
    wood = wood if wood in WOODS else "spruce"
    stock = ["barrel[facing=up]", "chest[facing=south]", "hay_block", "white_wool", "brown_wool", "barrel[facing=up]"]
    back = [(x, 1, 1, stock[int(c.rng.integers(len(stock)))]) for x in range(2, w - 3)]
    back += [(x, 2, 1, "barrel[facing=up]" if x % 3 == 0 else f"{wood}_shelf[facing=south,powered=false,side_chain=unconnected]")
             for x in range(2, w - 3)]                                     # shelves of goods over the stock (#526)
    c.goods = ("wheat", "bread", "apple", "carrot", "potato", "melon_slice", "leather", "white_wool", "paper",
               "emerald", "honey_bottle", "egg")
    counter = [(x, 1, d - 3, f"{wood}_slab[type=top]") for x in range(3, w - 3) if abs(x - w // 2) > 1]
    c.furniture(back + counter + [(4, 2, d - 3, "cartography_table"),
                                (w - 5, 2, d - 3, "lectern[facing=south,has_book=true,powered=false]")])
    if h >= 7:                                                             # upper floor over a ladder, lit from below
        c.box(2, w - 2, 4, 5, 1, d - 1, st.wood)
        c.box(w - 3, w - 2, 1, 5, 1, 2, "ladder[facing=south]")
        c.furniture([(x, 3, 2, "lantern[hanging=true]") for x in (5, w - 6)]
                  + [(x, 5, z, stock[(x + z) % len(stock)]) for x in range(2, w - 4) for z in (1, 2) if x % 4]
                  + [(w // 2, 5, 3, "lantern[hanging=false]")])
    else:
        c.furniture([(w // 2 - 2, h, 2, "lantern[hanging=true]")])
    c.flag(w - 2, top + 1, d // 2, col, 2)
    # Lean-to stalls on the west, south and east sides; the gap in the middle of the south row is the entrance
    goods = ["barrel[facing=up]", "hay_block", "melon", "pumpkin", "chest[facing=south]", "composter"]
    stairs = family(st.roof)[0]
    gate = range(w // 2 - 1, w // 2 + 2)
    rows = [(x, z, "north", (x, w - 1)) for x in range(w) for z in range(w - 2, w)]
    rows += [(x, z, "east" if x < 2 else "west", (0 if x < 2 else w - 1, z))
             for x in (0, 1, w - 2, w - 1) for z in range(d + 1, w - 2)]
    for x, z, face, (ox, oz) in rows:
        depth = abs(x - ox) + abs(z - oz)                                  # 0 = outer edge, 1 = inner edge
        if st.shape == "flat":                                             # cloth awnings in stripes
            c.set(x, 4, z, f"{col}_wool" if (x + z) % 2 else "white_wool")
        else:
            c.set(x, 3 + depth, z, stair(stairs, face))
        open_ = face == "north" and x in gate
        on_post = (x % 3 == 0 or x == w - 1) if face == "north" else (z - d - 1) % 3 == 0 or z == w - 3
        if on_post and not open_:
            c.box(x, x + 1, 1, 4 if st.shape == "flat" else 3 + depth, z, z + 1, f"{wood}_fence")
        elif depth == 0 and not open_ and c.rng.random() < 0.7:            # goods on the counter
            c.set(x, 1, z, goods[int(c.rng.integers(len(goods)))])
    # Trading table in the yard
    tx, tz = w // 2 - 1, (d + w - 2) // 2
    c.box(tx, tx + 3, 1, 2, tz, tz + 2, f"{wood}_slab[type=top]")
    c.set(tx, 2, tz, "barrel[facing=up]"); c.set(tx + 2, 2, tz + 1, "chest[facing=south]")


def caravanserai(c, w, st, col, T, ctx):
    """Caravanserai (Hindustanis): a square inn of sandstone around an open courtyard. A checkered base, rows of
    small arched windows, arched gates in the south and north walls, an arcade around the court, small domes
    along the flat roof and two large domes (one gilded) on the corners. The game has one model for all sets."""
    wall, flat, mid = "cut_sandstone", "smooth_sandstone", w // 2
    t = max(3, (w // 4) | 1)                                               # ring depth, odd: domes sit on its axis
    h = 5 if w >= 12 else 4
    c.box(0, w, 0, 1, 0, w, flat)
    c.room(0, w, 0, w, 0, h, wall)
    c.box(t, w - t, 1, h + 1, t, w - t, "air")                             # the courtyard
    c.walls(t - 1, w - t + 1, 1, h + 1, t - 1, w - t + 1, wall)
    for x in range(w):                                                     # checkered base of the outer walls
        for z in range(w):
            if (x in (0, w - 1) or z in (0, w - 1)) and (x + z) % 2 == 0:
                c.box(x, x + 1, 1, 2, z, z + 1, "polished_deepslate")
            if (x in (0, w - 1) or z in (0, w - 1)) and (x + z) % 2 == 1:
                c.box(x, x + 1, 2, 3, z, z + 1, "polished_deepslate")
    c.walls(0, w, h, h + 1, 0, w, "blue_terracotta")                       # glazed tile band under the roof
    for k in range(2, w - 2, 2):                                           # small arched windows, no shutters
        for x, z in ((k, 0), (k, w - 1), (0, k), (w - 1, k)):
            c.box(x, x + 1, 3, h - 1, z, z + 1, "glass_pane")
            c.set(x, h - 1, z, "chiseled_sandstone")
    for k in range(t, w - t, 2):                                           # arcade around the court
        for x, z in ((k, t - 1), (k, w - t), (t - 1, k), (w - t, k)):
            c.box(x, x + 1, 1, 3, z, z + 1, "air")
    for x, face in ((0, "east"), (w - 1, "west")):                         # doors east and west
        c.box(x, x + 1, 1, 4, mid - 2, mid + 1, "chiseled_sandstone")
        c.door(x, 1, mid - 1, face, wood="acacia")
    # Flat roof over the ring with a parapet, small domes along its axis and two large domes on the corners
    c.box(0, w, h + 1, h + 2, 0, w, flat)
    c.box(t, w - t, h + 1, h + 2, t, w - t, "air")
    c.walls(0, w, h + 2, h + 3, 0, w, "sandstone_wall")
    a, b = t // 2, w - 1 - t // 2
    for k in range(a + 3, b - 1, 3):
        for x, z in ((k, a), (k, b), (a, k), (b, k)):
            c.dome(x, z, 1.2, h + 2, flat)
    c.cylinder(a, a, 1.6, h + 2, h + 3, wall)                              # drum
    top = c.dome(a, a, 2.2, h + 3, flat)
    c.set(a, top + 1, a, "lightning_rod")
    top = c.dome(b, b, 2.2, h + 2, "gold_block")                           # the gilded dome
    c.set(b, top + 1, b, "lightning_rod")
    c.dome(a, b, 1.2, h + 2, flat); c.dome(b, a, 1.2, h + 2, flat)
    for z0, z1, zo in ((0, t, 0), (w - t, w, w - 1)):                       # arched gates south and north
        c.box(mid - 3, mid + 3, h, h + 4, zo, zo + 1, wall)                    # the portal rises over the roof
        c.box(mid - 3, mid + 3, h + 4, h + 5, zo, zo + 1, "chiseled_sandstone")
        c.box(mid - 2, mid + 2, h, h + 2, zo, zo + 1, "blue_terracotta")       # tile panel over the arch
        c.box(mid - 1, mid + 1, 1, h - 1, z0, z1, "air")
        for z in (z0, z1 - 1):
            c.set(mid - 2, h - 1, z, "chiseled_sandstone"); c.set(mid + 1, h - 1, z, "chiseled_sandstone")
            c.set(mid - 1, h - 1, z, stair("sandstone_stairs", "west", half="top"))
            c.set(mid, h - 1, z, stair("sandstone_stairs", "east", half="top"))
    c.flag(b, h + 2, a + 2, col, 2)
    c.banner(mid - 3, h - 1, w, col); c.banner(mid + 2, h - 1, w, col)
    # The court: a water trough and goods of the caravans
    c.set(mid, 1, mid, "water_cauldron[level=3]")
    for x, z, g in ((t, t, "barrel[facing=up]"), (w - t - 1, t, "hay_block"), (t, w - t - 1, "chest[facing=east]")):
        c.set(x, 1, z, g)
    # The rooms in the ring: bales of goods in the corners, barrels along the sides, a carpet and lanterns
    ring = sorted({p for k in range(1, w - 1) for p in ((k, 1), (k, w - 2), (1, k), (w - 2, k))})
    bales = ["white_wool", "orange_wool", "red_wool", "hay_block"]
    items = []
    for x, z in ring:
        if x in (1, w - 2) and z in (1, w - 2):
            items += [(x, 1, z, "hay_block"), (x, 2, z, bales[int(c.rng.integers(len(bales)))])]
        elif (x + z) % 4 == 0:
            items += [(x, 1, z, "barrel[facing=up]" if c.rng.random() < 0.6 else bales[int(c.rng.integers(len(bales)))])]
        elif (x + z) % 4 == 2:
            items += [(x, h, z, "lantern[hanging=true]")]
    items += [(x, 1, z, "red_carpet") for x, z in ring]
    c.furniture(items)


def monastery(c, w, st, col, T, ctx):
    stone = st.stone
    c.box(0, w, 0, 1, 0, w, st.stone2)
    nw = max(5, w - 2 * max(1, w // 6))
    x0 = (w - nw) // 2
    x1 = x0 + nw
    hn = max(5, round(w * 0.5))
    t = 3 if w < 12 else 4
    c.room(x0, x1, 1, w, 0, hn, stone, st.floor)
    furnish_worship(c, x0 + 1, x1 - 1, 2, w - 1, 1, "mosque" if st.domes else "shrine" if st.shape == "asian" else "chapel", st,
            aisle=w // 2)
    for z in range(3, w - t, 3):                                          # tall windows
        c.box(x0, x0 + 1, 2, hn - 1, z, z + 1, "yellow_stained_glass_pane")
        c.box(x1 - 1, x1, 2, hn - 1, z, z + 1, "light_blue_stained_glass_pane")
        c.box(x0 - 1, x0, 1, 3, z - 1, z, stone); c.box(x1, x1 + 1, 1, 3, z - 1, z, stone)   # buttresses
    mid = w // 2
    if st.domes:
        c.flat_roof(x0, x1, 1, w, hn + 1, st.roof, parapet=st.plaster)
        c.cylinder((x0 + x1 - 1) / 2, w / 2 - 1, nw / 2 - 0.5, hn + 2, hn + 4, st.plaster)
        top = c.dome((x0 + x1 - 1) / 2, w / 2 - 1, nw / 2 - 0.5, hn + 4, st.dome)
        c.set(mid, top + 1, w // 2 - 1, "lightning_rod")
        c.cylinder(x0 + 0.5, w - 1.5, 1, 1, hn + 6, st.plaster)            # minaret
        c.cone(x0 + 0.5, w - 1.5, 1.5, hn + 6, st.dome)
    else:
        c.gable(x0 - 1, x1 + 1, 0, w + 1, hn, st.roof if st.shape != "flat" else "deepslate_tile",
                fill=(x0, x1, 1, w, stone), axis="z")
        rc, ry = (x0 + x1 - 1) // 2, hn + 2                                 # rose window in the front gable
        for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
            c.set(rc + dx, ry + dy, w - 1, "yellow_stained_glass_pane" if dx or dy else "red_stained_glass_pane")
        # Bell tower at the front west corner, as in the game: the facade with the door stays free
        tx0 = max(0, x0 - 1)
        th = hn + nw // 2 + 4
        c.room(tx0, tx0 + t, w - t, w, 0, th, stone)
        c.box(tx0 + 1, tx0 + t - 1, th - 2, th, w - t, w, "air")
        c.box(tx0, tx0 + t, th - 2, th, w - t + 1, w - 1, "air")
        c.walls(tx0, tx0 + t, th - 2, th, w - t, w, "air")
        for x in (tx0, tx0 + t - 1):
            for z in (w - t, w - 1):
                c.box(x, x + 1, th - 2, th, z, z + 1, stone)
        c.set(tx0 + t // 2, th - 1, w - 1 - t // 2, "bell[attachment=ceiling,facing=south]")
        c.box(tx0, tx0 + t, th, th + 1, w - t, w, stone)
        c.spire(tx0, tx0 + t, w - t, w, th + 1, family(st.roof if st.shape != "flat" else "deepslate_tile")[2],
                steep=3, tip="lightning_rod")
    c.box(mid, mid + 1, 1, 4, w - 1, w, "air")
    c.door(mid, 1, w - 1, wood="dark_oak")
    c.banner(mid - 1 if t > 3 else mid - 2, 4, w, col); c.banner(mid + 1 if t > 3 else mid + 2, 4, w, col)


def fortified_church(c, w, st, col, T, ctx):
    """Armenian and Georgian Fortified Church (#128): a cross-domed stone church with a drum and a cone roof in the
    middle, inside a wall with merlons, a round tower at the front west corner and an open bell tower at the front
    east corner. The game has one model for all sets: light stone and orange tile roofs."""
    s = w / 12                                                            # the design is drawn for 3 tiles
    S = lambda v: max(1, round(v * s))
    wall, roof, band = "stone_bricks", "red_sandstone", f"{col}_wool"   # red_sandstone: the orange roof tiles
    c.box(0, w, 0, 1, 0, w, st.stone2)
    # Curtain wall with merlons and a band in the player color
    wh = S(4)
    c.walls(0, w, 1, wh + 1, 0, w, wall)
    c.walls(0, w, wh, wh + 1, 0, w, band)
    c.crenels(0, w, 0, w, wh + 1, wall)
    for z in range(S(2), w - S(4), 3):                                    # arrow slits
        c.set(0, 2, z, "iron_bars"); c.set(w - 1, 2, z, "iron_bars")
    # The church: a nave along z and a transept along x, gable roofs, a drum with a cone roof on the crossing
    h = S(7)
    nx0, nx1, nz0, nz1 = S(4), w - S(3), S(1), w - S(2)                   # nave
    tx0, tx1, tz0, tz1 = S(2), w - S(1), S(2), S(7)                       # transept
    c.room(nx0, nx1, nz0, nz1, 0, h, wall, st.floor)
    c.room(tx0, tx1, tz0, tz1, 0, h, wall, st.floor)
    c.box(nx0 + 1, nx1 - 1, 1, h + 1, nz0 + 1, nz1 - 1, "air")
    c.box(tx0 + 1, tx1 - 1, 1, h + 1, tz0 + 1, tz1 - 1, "air")
    furnish_worship(c, nx0 + 1, nx1 - 1, nz0 + 1, nz1 - 1, 1, "chapel", st, aisle=(S(3) + w - S(3)) // 2 + 1)
    c.gable(tx0 - 1, tx1 + 1, tz0 - 1, tz1 + 1, h + 1, roof, fill=(tx0, tx1, tz0, tz1, wall), axis="x")
    ridge = c.gable(nx0 - 1, nx1 + 1, nz0 - 1, nz1 + 1, h + 1, roof, fill=(nx0, nx1, nz0, nz1, wall), axis="z")
    for x, z in ((nx0, (nz0 + nz1) // 2 + 2), (nx1 - 1, (nz0 + nz1) // 2 + 2)):
        c.box(x, x + 1, h - 3, h - 1, z, z + 1, "yellow_stained_glass_pane")
    for x in ((tx0 + nx0) // 2, (nx1 + tx1 - 1) // 2):                    # tall windows in the transept
        c.box(x, x + 1, h - 3, h - 1, tz1 - 1, tz1, "yellow_stained_glass_pane")
        c.box(x, x + 1, h - 3, h - 1, tz0, tz0 + 1, "yellow_stained_glass_pane")
    cx, cz, r = (nx0 + nx1 - 1) / 2, (tz0 + tz1 - 1) / 2, max(1.0, 1.5 * s)
    dy = ridge + 1
    c.cylinder(cx, cz, r, ridge - 1, dy + S(4), wall)
    for ox, oz in ((r, 0), (-r, 0), (0, r), (0, -r)):                     # windows of the drum
        c.box(round(cx + ox), round(cx + ox) + 1, dy, dy + S(2), round(cz + oz), round(cz + oz) + 1,
              "yellow_stained_glass_pane")
    c.cylinder(cx, cz, r + 0.5, dy + S(4), dy + S(4) + 1, band)
    top = c.cone(cx, cz, r + 0.5, dy + S(4) + 1, roof, step=2)
    c.set(int(cx), top + 1, int(cz), "lightning_rod")
    # Round tower at the front west corner, with a cone roof
    rr, rx, rz, rh = 1.8 * s, S(1.5), w - 1 - S(1.5), S(6)
    c.cylinder(rx, rz, rr, 1, rh, wall)
    c.cylinder(rx, rz, rr + 0.5, rh, rh + 1, band)
    t = c.cone(rx, rz, rr + 0.5, rh + 1, roof, step=2)
    c.set(int(rx), t + 1, int(rz), "lightning_rod")
    c.set(int(rx + rr), S(4), int(rz), "iron_bars")
    # Bell tower at the front east corner: a square tower, an open belfry and a hip roof
    b0, bh = w - S(3), S(9)
    c.box(b0, w, 1, bh, b0, w, wall)
    c.walls(b0, w, bh - 1, bh, b0, w, band)
    c.box(b0, w, bh, bh + 2, b0, w, "air")
    for x in (b0, w - 1):
        for z in (b0, w - 1):
            c.box(x, x + 1, bh, bh + 2, z, z + 1, "stone_brick_wall")
    c.set((b0 + w - 1) // 2, bh + 1, (b0 + w - 1) // 2, "bell[attachment=ceiling,facing=south]")
    c.box(b0, w, bh + 2, bh + 3, b0, w, wall)
    t = c.hip(b0 - 1, w + 1, b0 - 1, w + 1, bh + 3, roof)
    c.set((b0 + w - 1) // 2, t + 1, (b0 + w - 1) // 2, "lightning_rod")
    c.set((b0 + w - 1) // 2, S(5), w - 1, "yellow_stained_glass_pane")
    # Gate in the front wall between the towers, the church door behind it
    gx = (S(3) + b0) // 2 + 1
    c.box(gx, gx + 1, 1, 4, w - 1, w, "air")
    c.set(gx, 3, w - 1, "chiseled_stone_bricks")
    c.door(gx, 1, w - 1, wood="dark_oak")
    c.box(gx, gx + 1, 1, 3, nz1 - 1, nz1, "air")
    c.door(gx, 1, nz1 - 1, wood="dark_oak")
    c.banner(gx - 1, 3, w, col); c.banner(gx + 1, 3, w, col)


def university(c, w, st, col, T, ctx):
    """Like the game: a hall of two floors at the back with a library inside, a higher block on the east side
    and a scholar statue in the front yard. Sets with domes keep a domed hall (the observatory) behind columns."""
    c.box(0, w, 0, 1, 0, w, st.stone2)
    mid = w // 2
    if st.domes:
        h = max(5, round(w * 0.45))
        c.room(1, w - 1, 1, w - 2, 0, h, st.stone if st.shape != "flat" else st.plaster, st.floor)
        c.windows(1, w - 1, 1, w - 2, 3, step=2, height=2)
        library(c, 2, w - 2, 2, 4)
        study(c, 2, w - 3, 3, w - 4)
        for x in range(1, w - 1, 2):                                      # columns in front
            c.box(x, x + 1, 1, h + 1, w - 1, w, "quartz_pillar")
        c.box(0, w, h + 1, h + 2, 1, w, "smooth_quartz" if st.shape != "flat" else family(st.roof)[2])
        c.box(mid, mid + 1, 1, 3, w - 2, w - 1, "air")
        c.door(mid, 1, w - 3)                                             # in the south wall of the hall
        hang(c, mid, h - 1, (w - 1) // 2)
        r = max(1.5, w / 4 - 0.5)                                         # observatory dome
        cx = (w - 1) / 2
        c.cylinder(cx, cx - 1, r, h + 2, h + 4, st.plaster)
        top = c.dome(cx, cx - 1, r, h + 4, st.dome)
        c.set(mid, top + 1, int(cx - 1), "lightning_rod")
        c.banner(1, h - 1, w, col); c.banner(w - 2, h - 1, w, col)
        return
    m = inset(w)
    h = max(6, round(w * 0.5))                                            # two floors
    zb = m + max(4, w // 2)                                               # hall: z m .. zb-1
    tx = w - m - max(4, w // 3)                                           # east block: x tx .. w-m-1
    c.timber_room(m, tx + 1, m, zb, 0, h, st)
    c.windows(m, tx + 1, m, zb, 2, sides="nws", step=2)
    c.windows(m, tx + 1, m, zb, h // 2 + 2, sides="nws", step=2)
    library(c, m + 1, tx, m + 1, zb - m - 3)
    dx = (m + tx) // 2
    study(c, m + 1, tx - 1, m + 2, zb - 2)
    c.door(dx, 1, zb - 1)
    c.roof(m, tx + 1, m, zb, h + 1, st, axis="x")
    hang(c, dx, h - 1, (m + zb) // 2)
    th = h + 2                                                            # the higher east block, to the front
    c.timber_room(tx, w - m, m, w - m - 1, 0, th, st)
    c.windows(tx, w - m, m, w - m - 1, 2, sides="es", step=2)
    c.windows(tx, w - m, m, w - m - 1, th // 2 + 2, sides="es", step=2)
    if st.shape in ("gable", "hip", "asian"):
        c.hip(tx - 1, w - m + 1, m - 1, w - m, th, st.roof, flare=st.shape == "asian")
    else:
        c.roof(tx, w - m, m, w - m - 1, th + 1, st)
    c.door(tx + 1, 1, w - m - 2, facing="south")
    if w - m - tx >= 4:                                                   # the reading room of the east block
        ex = w - m - 2
        c.box(ex, ex + 1, 1, 3, m + 1, w - m - 4, "bookshelf")
        c.set(ex, 3, m + 1, "candle[candles=2,lit=true,waterlogged=false]")
        c.set(tx + 1, 1, m + 1, "lectern[facing=north,has_book=true,powered=false]")
        hang(c, tx + 1, th - 1, w // 2 - 1)
    sx, sz = (m + tx) // 2 - 1, (zb + w) // 2                             # scholar statue in the yard
    c.set(sx, 1, sz, "chiseled_stone_bricks")
    c.box(sx, sx + 1, 2, 4, sz, sz + 1, "quartz_pillar")
    c.set(sx, 4, sz, "chiseled_quartz_block")
    c.banner(dx + 1, 3, zb, col); c.banner(tx + 2, 4, w - m - 1, col)


def hang(c, x, y, z):
    """A hanging lantern at (x, y, z) on a chain up to the first block above it (none if there is no block)."""
    air = (-1, c.B("air"))
    top = next((t for t in range(y + 1, c.height) if c.get(x, t, z) not in air), None)
    if top is not None:
        c.box(x, x + 1, y + 1, top, z, z + 1, "iron_chain")
        c.set(x, y, z, "lantern[hanging=true]")


def study(c, x0, x1, z0, z1):
    """The desks of a library room (x0..x1, z0..z1 inside, the shelves behind z0): an enchanting table at the
    shelves and a cartography table with candles in the front corner. Candles on the shelves light the room."""
    if x1 - x0 < 3 or z1 - z0 < 1:
        return
    c.set(x1, 1, z0, "enchanting_table")
    c.set(x1, 1, z1, "cartography_table")
    c.set(x1, 2, z1, "candle[candles=3,lit=true,waterlogged=false]")
    for x in (x0, x1):
        c.set(x, 3, z0 - 1, "candle[candles=1,lit=true,waterlogged=false]")


def library(c, x0, x1, z, rows):
    """Bookshelves along the back wall (z) and lecterns with books in front of them."""
    c.box(x0, x1, 1, 3, z, z + 1, "bookshelf")
    for x in range(x0 + 1, x1 - 1, 3):
        c.set(x, 1, z + min(2, rows), "lectern[facing=north,has_book=true,powered=false]")


def furnish_worship(c, x0, x1, z0, z1, y, kind, st, aisle=None):
    """Furniture of a hall of worship (#253): the room inside the walls is x0..x1-1, z0..z1-1, the floor blocks
    are at y-1. The altar (chapel), the mihrab (mosque) or the statue (shrine) is at the back (z0), the main door
    in the south wall. The aisle (default: the middle) and the row in front of the door stay free. Lit candles
    and lanterns light the room."""
    if x1 - x0 < 3 or z1 - z0 < (2 if kind == "shrine" else 4):
        return
    mid = (x0 + x1 - 1) // 2 if aisle is None else aisle
    wood = st.wood.replace("_planks", "")
    wood = wood if wood in WOODS else "spruce"
    candles = "candle[candles=3,lit=true,waterlogged=false]"
    lantern = "lantern[hanging=false,waterlogged=false]"
    for x in (x0, x1 - 1):                                                # lanterns in the back corners
        c.set(x, y, z0, lantern)
    if kind == "mosque":
        c.box(x0, x1, y, y + 1, z0 + 1, z1 - 1, "red_carpet")              # prayer carpets in rows
        for z in range(z0 + 2, z1 - 1, 3):
            c.box(x0, x1, y, y + 1, z, z + 1, "white_carpet")
        c.box(mid, mid + 1, y, y + 2, z0, z0 + 1, st.dome)                # mihrab: a tiled niche in the qibla wall
        c.set(mid - 1, y, z0, candles)
        if mid + 3 < x1:                                                  # minbar: a stair to the west of it
            c.set(mid + 1, y, z0, stair(f"{wood}_stairs", "east"))
            c.set(mid + 2, y, z0, f"{wood}_planks"); c.set(mid + 2, y + 1, z0, stair(f"{wood}_stairs", "east"))
        c.set(mid, y, z0 + 2, "lectern[facing=south,has_book=true,powered=false]")
        return
    if kind == "shrine":
        c.set(mid, y, z0, "chiseled_stone_bricks")                         # statue with a gold head
        c.set(mid, y + 1, z0, "gold_block")
        for x in (mid - 1, mid + 1):
            c.set(x, y, z0, candles)
        return
    a0, a1 = max(x0, mid - 1), min(x1, mid + 2)                            # chapel: altar with candles
    c.box(a0, a1, y, y + 1, z0, z0 + 1, "chiseled_stone_bricks")
    c.set(a0, y + 1, z0, candles); c.set(a1 - 1, y + 1, z0, candles)
    c.set(mid, y, z0 + 1, "lectern[facing=south,has_book=true,powered=false]")
    for z in range(z0 + 3, z1 - 1, 2):                                    # pews: the backrest is on the south side
        for x in range(x0, x1):
            if x != mid:
                c.set(x, y, z, stair(f"{wood}_stairs", "south"))


def throne_hall(c, x0, x1, z0, z1, y, st, col, aisle=None):
    """Furniture of a Wonder hall (#336), the same room convention as furnish_worship: a throne at the back (z0)
    between two gold blocks with lanterns, banners in the player color over it, a carpet in the player color to
    the door, the treasure (chests, gold) in the back corners, pillars along the carpet and lecterns in a large
    hall. The aisle and the row in front of the door stay free."""
    if x1 - x0 < 3 or z1 - z0 < 2:
        return
    mid = (x0 + x1 - 1) // 2 if aisle is None else aisle
    wood = st.wood.replace("_planks", "")
    wood = wood if wood in WOODS else "spruce"
    chest = "chest[facing=south,type=single,waterlogged=false]"
    for x, dx in ((x0, 1), (x1 - 1, -1)):                                 # the treasure
        if abs(x - mid) >= 2:
            c.set(x, y, z0, chest)
        if abs(x + dx - mid) >= 2:
            c.set(x + dx, y, z0, "gold_block")
    c.set(mid, y, z0, stair(f"{wood}_stairs", "north"))                   # the throne: the backrest is on the north side
    for x in (mid - 1, mid + 1):
        c.set(x, y, z0, "gold_block"); c.set(x, y + 1, z0, "lantern[hanging=false,waterlogged=false]")
    for x in {mid, max(x0, mid - 2), min(x1 - 1, mid + 2)}:
        c.banner(x, y + 2, z0, col)
    c.box(mid, mid + 1, y, y + 1, z0 + 1, z1 - 1, f"{col}_carpet")
    if x1 - x0 < 7 or z1 - z0 < 5:
        return
    air = (-1, c.B("air"))
    for z in range(z0 + 2, z1 - 1, 3):
        for x in (mid - 2, mid + 2):
            top = next((t for t in range(y, c.height) if c.get(x, t, z) not in air), y + 3)
            c.box(x, x + 1, y, top, z, z + 1, "quartz_pillar")
    zl = (z0 + z1) // 2
    c.set(x0, y, zl, "lectern[facing=east,has_book=true,powered=false]")
    c.set(x1 - 1, y, zl, "lectern[facing=west,has_book=true,powered=false]")


def reach(c, x, y, z, dx, dz):
    """The last air cell from (x, y, z) in the direction (dx, dz): the cell in front of the wall of a round room."""
    air = c.id("air")
    while c.get(x + dx, y, z + dz) == air:
        x, z = x + dx, z + dz
    return x, z


def mill(c, w, st, col, T, ctx):
    if st.mill != "windmill":
        return granary(c, w, st, col, T, ctx)
    c.box(0, w, 0, 1, 0, w, st.stone2)
    cx = (w - 1) / 2
    r = w / 2 - 0.6
    hb = max(7, round(w * 1.3))
    c.cylinder(cx, cx, r, 1, 3, st.stone)
    c.cylinder(cx, cx, r - 0.4, 3, hb, st.plaster)
    c.cylinder(cx, cx, r - 1.4, 1, hb, "air")
    c.cylinder(cx, cx, r + 0.3, hb, hb + 1, st.wood)
    c.cone(cx, cx, r + 0.3, hb + 1, family(st.roof)[2] if st.shape != "flat" else "dark_oak_planks")
    mid = w // 2
    zf = int(round(cx + r))                                                # south face
    c.door(mid, 1, zf)
    c.set(mid, 5, zf, "glass_pane")
    # Sails: an X of four arms in front of the south face
    hub_y = hb - 1
    hz = zf + 1
    c.set(mid, hub_y, hz, "stripped_spruce_log[axis=z]")
    L = min(hub_y - 2, max(4, round(w * 0.8)))
    for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        for i in range(1, L + 1):
            c.set(mid + sx * i, hub_y + sy * i, hz, "spruce_fence")
            if i > 1:
                c.set(mid + sx * i - sx, hub_y + sy * i, hz, "white_wool")
    c.banner(mid + 1, 3, zf, col)
    c.set(0, 1, w - 1, "barrel[facing=up]"); c.set(1, 1, w - 1, "hay_block")             # flour and grain sacks
    c.set(w - 1, 1, 1, "grindstone[face=floor,facing=south]")                          # millstone
    mill_room(c, cx, mid, zf, shaft=hb - 1)


def mill_room(c, cx, mid, zf, shaft=None, lamp=None):
    """Inside of a round mill (#255): a millstone in the middle (with the drive shaft of a windmill above it),
    grain sacks and barrels at the wall and a lantern. The way from the door to the millstone stays free."""
    z = zf - 1
    while z > cx and c.get(mid, 1, z) not in (-1, c.id("air")):           # the door leads into the room
        c.box(mid, mid + 1, 1, 3, z, z + 1, "air")
        z -= 1
    lo, hi = int(cx) - 1, int(cx) + 2                                      # the free floor inside the wall
    c.set(lo + 1, 1, lo + 1, "grindstone[face=floor,facing=south]")
    if shaft:
        c.box(lo + 1, lo + 2, 2, shaft + 1, lo + 1, lo + 2, "stripped_spruce_log[axis=y]")
    c.set(lo, 1, lo, "hay_block"); c.set(lo, 2, lo, "hay_block"); c.set(lo, 1, lo + 1, "hay_block")
    c.set(hi, 1, lo, "barrel[facing=up]"); c.set(lo, 1, hi, "barrel[facing=up]")
    c.set(hi, 2, lo, "lantern[hanging=false]")
    c.free_bed(1, [(x, z, f) for f in ("west", "north") for x in (hi, lo, hi - 1) for z in range(lo, hi + 1)
                   if mid not in (x, x + (f == "west"))])                  # the miller's straw bed, off the way in
    if lamp:
        c.set(lo + 1, lamp, lo + 1, "lantern[hanging=true]")


def folwark(c, w, st, col, T, ctx):
    """Polish Folwark (#126): a farmstead. A two-storey half-timbered hall at the back, a barn wing with a stone base
    and a wide door at the front right, a small post windmill on the west side and a fenced garden in front.
    The game has one model for all sets: white plaster, dark timber and red tile roofs."""
    import dataclasses
    s = w / 12                                                            # the design is drawn for 3 tiles
    S = lambda v: max(1, round(v * s))
    fw = dataclasses.replace(st, plaster="white_terracotta", timber="dark_oak_log", beam="stripped_dark_oak_log",
                             stone="cobblestone", floor="spruce_planks", framing="timber", torons=False)
    roof = "brick"                                                        # terracotta roof tiles
    c.box(0, w, 0, 1, 0, w, st.stone2)
    # Hall: two storeys, ridge along x, windows on both floors
    hx0, hx1, hz0, hz1, hh = S(4), w, S(1), S(6), S(7)
    c.timber_room(hx0, hx1, hz0, hz1, 0, hh, fw)
    for y in (3, hh - 1):
        c.windows(hx0, hx1, hz0, hz1, y, step=2, sides="sn")
    c.door(hx0 + 2, 1, hz1 - 1)
    c.banner(hx0 + 1, hh // 2 + 1, hz1, col)
    c.gable(hx0 - 1, hx1, hz0 - 1, hz1 + 1, hh + 1, roof, fill=(hx0, hx1, hz0, hz1, fw.plaster), axis="x")
    # Barn wing at the front right: stone base, ridge along z, wide open door to the south
    bx0, bz0, bh = S(8), hz1, S(5)
    c.timber_room(bx0, w, bz0, w - 1, 0, bh, fw, low_stone=2)
    c.box(bx0 + 1, w - 1, 1, 4, w - 2, w - 1, "air")
    c.set(bx0 + 1, 1, w - 3, "hay_block"); c.set(w - 2, 1, w - 3, "hay_block"); c.set(w - 2, 2, w - 3, "hay_block")
    c.windows(bx0, w, bz0, w - 1, bh - 1, step=2, sides="w")
    c.gable(bx0 - 1, w + 1, bz0, w, bh + 1, roof, fill=(bx0, w, bz0, w - 1, fw.plaster), axis="z")
    # Post windmill on the west side: a tower above the hall, large sails on its south face
    mx0, mx1, mz0, mz1, mh = 0, S(4), S(4), S(8), S(11)
    c.timber_room(mx0, mx1, mz0, mz1, 0, mh, fw)
    c.door((mx0 + mx1) // 2, 1, mz1 - 1)
    c.set(mx0, mh - 3, (mz0 + mz1) // 2, "glass_pane"); c.set(mx0, 4, (mz0 + mz1) // 2, "glass_pane")
    c.gable(mx0 - 1, mx1 + 1, mz0 - 1, mz1 + 1, mh + 1, roof, fill=(mx0, mx1, mz0, mz1, fw.plaster), axis="z")
    hub_x, hub_y, hz = (mx0 + mx1) // 2, mh - 2, mz1
    c.set(hub_x, hub_y, hz, "stripped_spruce_log[axis=z]")
    L = hub_y - 5                                                         # arms stay above head height
    for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        for i in range(1, L + 1):
            c.set(hub_x + sx * i, hub_y + sy * i, hz, "spruce_fence")
            if i > 1:
                c.set(hub_x + sx * i - sx, hub_y + sy * i, hz, "white_wool")
    # Garden with a fence in front, goods next to the doors
    gx0, gx1, gz0 = S(1), S(7), S(9)
    c.box(gx0, gx1, 0, 1, gz0, w - 1, "farmland[moisture=7]")
    for x in range(gx0, gx1):
        for z in range(gz0, w - 1):
            c.set(x, 1, z, ["carrots[age=7]", "potatoes[age=7]", "wheat[age=7]"][(x + z) % 3])
    c.walls(gx0 - 1, gx1 + 1, 1, 2, gz0 - 1, w, "spruce_fence")
    c.set((gx0 + gx1) // 2, 1, gz0 - 1, "spruce_fence_gate[facing=north,in_wall=false,open=false,powered=false]")
    c.set(mx1, 1, mz1, "barrel[facing=up]"); c.set(mx1 + 1, 1, mz1, "barrel[facing=up]")
    c.set(0, 1, mz1, "spruce_trapdoor[facing=south,half=bottom,open=true]")   # cart wheel against the wall
    c.set(bx0 - 1, 1, w - 2, "composter")
    # Inside: the home of the steward in the hall, sacks of grain in the barn, the millstone in the windmill
    furnish(c, hx0 + 1, hx1 - 1, hz0 + 1, hz1 - 1, 1, fw, col, door=hx0 + 2)
    c.furniture([(hx1 - 2, 1, hz0 + 1, "barrel[facing=up]"), (hx0 + 1, hh, (hz0 + hz1) // 2, "lantern[hanging=true]"),
                 (hx1 - 2, hh, (hz0 + hz1) // 2, "lantern[hanging=true]"),
                 (bx0 + 1, 1, bz0 + 1, "hay_block"), (bx0 + 1, 2, bz0 + 1, "hay_block"), (w - 2, 1, bz0 + 1, "hay_block"),
                 ((bx0 + w) // 2, bh, bz0 + 2, "lantern[hanging=true]"),
                 (mx0 + 1, 1, mz0 + 1, "grindstone[face=floor,facing=north]"), (mx1 - 2, 1, mz0 + 1, "hay_block"),
                 (mx1 - 2, 2, mz0 + 1, "lantern[hanging=false]")])


def granary(c, w, st, col, T, ctx):
    """Mill for the other architecture sets: round store with a pointed roof and millstones."""
    c.box(0, w, 0, 1, 0, w, st.stone2)
    cx = (w - 1) / 2
    r = w / 2 - 0.8
    h = max(4, round(w * 0.6))
    c.cylinder(cx, cx, r, 1, h + 1, st.plaster, hollow=True)
    c.cylinder(cx, cx, r + 0.5, h + 1, h + 2, st.wood)
    c.cone(cx, cx, r + 0.8, h + 2, "hay_block" if st.shape != "asian" else family(st.roof)[2])
    mid = w // 2
    zf = int(round(cx + r))
    c.door(mid, 1, zf)
    c.set(0, 1, w - 1, "grindstone[face=floor,facing=south]"); c.set(w - 1, 1, w - 1, "hay_block")
    c.banner(mid + 1, 3, zf, col)
    mill_room(c, cx, mid, zf, lamp=h)


def log_pile(c, x0, x1, z0, n, logs):
    """Logs along x, stacked as a pyramid: n logs at the bottom, one less on each layer."""
    for y in range(n):
        for k in range(n - y):
            c.box(x0, x1, 1 + y, 2 + y, z0 + k, z0 + k + 1, logs[(y + k) % len(logs)] + "[axis=x]")


def shelter(c, x0, x1, z0, z1, st):
    """Open shelter: four posts and a small roof above head height."""
    for x in (x0, x1 - 1):
        for z in (z0, z1 - 1):
            c.box(x, x + 1, 1, 4, z, z + 1, st.timber)
    c.box(x0, x1, 3, 4, z0, z0 + 1, st.beam + "[axis=x]"); c.box(x0, x1, 3, 4, z1 - 1, z1, st.beam + "[axis=x]")
    if st.shape == "flat":
        c.box(x0, x1, 4, 5, z0, z1, family(st.roof)[1] + "[type=bottom]")
    else:
        c.gable(x0, x1, z0 - 1, z1 + 1, 4, st.roof, axis="z")


def lumber_camp(c, w, st, col, T, ctx):
    """An open yard (as in the game): log piles, a hoist with a hanging log, a sawhorse and a workbench."""
    c.box(0, w, 0, 1, 0, w, "coarse_dirt")
    logs = [st.timber.replace("stripped_", ""), "spruce_log", "oak_log"]
    log_pile(c, 1, w - 3, w - 4, 3, logs)                                 # front: the large pile
    log_pile(c, w - 2, w, 1, 2, logs[1:])                                  # east: a small pile
    post = st.timber.replace("stripped_", "")
    c.box(1, 2, 1, 6, 1, 2, post)                                          # hoist: post, arm, chain, log
    c.box(1, 4, 6, 7, 1, 2, post + "[axis=x]")
    c.set(3, 5, 1, "iron_chain"); c.set(3, 4, 1, "oak_log[axis=x]")
    c.set(2, 5, 1, "lantern[hanging=true]")                               # light under the hoist arm
    c.set(4, 1, 2, "spruce_fence"); c.set(6, 1, 2, "spruce_fence")      # sawhorse with a log on it
    c.box(4, 7, 2, 3, 2, 3, "stripped_spruce_log[axis=x]")
    c.set(1, 1, 3, "crafting_table"); c.set(2, 1, 3, "oak_log")           # workbench, chopping block
    c.free_bed(1, [(x, z, f) for z in range(2, w - 1) for x in range(w - 1, 0, -1) for f in ("west", "north")],
               open_=True)                                                 # a straw bed in the yard
    c.flag(w - 1, 1, w - 1, col, 3)


def mining_camp(c, w, st, col, T, ctx):
    """An open yard (as in the game): a small shelter with tools, heaps of stone and gold, and a rail track."""
    c.box(0, w, 0, 1, 0, w, "coarse_dirt")
    shelter(c, 0, 5, 0, 4, st)
    c.set(1, 1, 1, "barrel[facing=up]"); c.set(2, 1, 1, "grindstone[face=floor,facing=south]")
    c.set(3, 1, 1, "chest[facing=south]")
    c.set(2, 2, 0, "lantern[hanging=true]")                               # light under the roof beam
    c.free_bed(1, [(x, z, f) for z in (2, 1) for x in (3, 2, 1) for f in ("north", "west")], open_=True)  # under the roof
    for x, z, h, b in ((w - 2, 1, 2, "cobblestone"), (w - 1, 1, 1, "stone"), (w - 2, 2, 1, "andesite"),
                       (w - 1, 2, 2, "cobblestone"), (w - 2, 3, 1, "cobblestone"),            # stone heap
                       (1, w - 3, 1, "gold_ore"), (2, w - 3, 2, "raw_gold_block"), (1, w - 2, 1, "raw_gold_block")):
        c.box(x, x + 1, 1, 1 + h, z, z + 1, b)
    for x in range(3, w - 1):
        c.set(x, 1, w - 2, "rail[shape=east_west]")
    c.set(w - 3, 1, w - 4, "cobblestone_slab[type=bottom]")
    c.flag(w - 1, 1, w - 1, col, 3)


def dock(c, w, st, col, T, ctx):
    """Dock: a timber house in the middle of a plank deck on piles, with steps down to the water and goods."""
    c.box(0, w, 1, 2, 0, w, "spruce_planks")                              # deck above the water
    for x in list(range(0, w, 3)) + [w - 1]:
        for z in list(range(0, w, 3)) + [w - 1]:
            c.box(x, x + 1, -8, 1, z, z + 1, "spruce_log")                 # piles
    # dark deck edge: an edge in the player color looks like the foundation ring of an unfinished dock (#2059)
    c.box(0, w, 1, 2, 0, 1, "dark_oak_planks"); c.box(0, 1, 1, 2, 0, w, "dark_oak_planks")
    c.box(w - 1, w, 1, 2, 0, w, "dark_oak_planks"); c.box(0, w, 1, 2, w - 1, w, "dark_oak_planks")
    m = w // 2
    for z in range(m - 1, m + 1):                                          # steps down to the water
        c.set(0, 1, z, "spruce_stairs[facing=east,half=bottom,shape=straight]")
        c.set(w - 1, 1, z, "spruce_stairs[facing=west,half=bottom,shape=straight]")
    x0, x1, z0, z1 = 2, w - 2, 2, w - 3
    c.timber_room(x0, x1, z0, z1, 1, 4, st)
    c.windows(x0, x1, z0, z1, 3, step=3)
    top = c.roof(x0, x1, z0, z1, 6, st, axis="z")
    c.door(m, 2, z1 - 1)
    c.banner(m - 1, 4, z1, col); c.banner(m + 1, 4, z1, col)
    c.set(m, 6, z1, "spruce_planks"); c.box(m, m + 1, 6, 7, z1 + 1, z1 + 2, "stripped_spruce_log[axis=z]")   # hoist
    c.set(m, 5, z1 + 1, "iron_chain")
    c.flag(m, top + 1, (z0 + z1) // 2, col, 2)
    # Inside (#255): goods and a lantern at the back wall, a net loom and a boat workbench at the side walls.
    # The way from the door to the back wall stays free.
    ix0, ix1, iz0 = x0 + 1, x1 - 2, z0 + 1
    for x, b in ((ix0, "barrel[facing=up]"), (ix0 + 1, "barrel[facing=up]"), (ix0 + 2, "chest[facing=south]"),
                 (ix1, "barrel[facing=up]")):
        c.set(x, 2, iz0, b)
    c.set(ix0 + 1, 3, iz0, "lantern[hanging=false]"); c.set(ix1, 3, iz0, "lantern[hanging=false]")
    c.set(ix0, 2, iz0 + 2, "loom[facing=east]"); c.set(ix0, 2, iz0 + 3, "hay_block")             # nets, ropes
    c.set(ix1, 2, iz0 + 2, "crafting_table"); c.set(ix1, 2, iz0 + 1, "spruce_slab[type=bottom]")  # boat work
    goods = ["barrel[facing=up]", "chest[facing=south]", "hay_block", "composter", "barrel[facing=up]"]
    for x, z in ((1, 1), (2, 1), (w - 2, 1), (w - 3, 1), (1, w - 2), (w - 2, w - 2), (w - 2, w - 3), (1, w - 3)):
        if c.rng.random() < 0.75:
            c.set(x, 2, z, goods[int(c.rng.integers(len(goods)))])
    for x in (0, w - 1):                                                   # bollards with rope
        for z in (0, w - 1):
            c.set(x, 2, z, "spruce_fence")


def harbor(c, w, st, col, T, ctx):
    """Harbor (Khmer): a sandstone pier on piles. A plinth with a band in the player color carries a stone house
    with an orange gable roof and a prang tower; stairs with guardian lions, a fish stall and a moored boat.
    Only the Khmer build it, so all sets use the same Khmer design."""
    sand, cut, chis = "smooth_sandstone", "cut_sandstone", "chiseled_sandstone"
    stone, relief = "stone_bricks", "chiseled_stone_bricks"               # grey stone of the house and the prang
    q = w - 3                                                              # water strip on the south-west side
    c.box(0, w, 1, 2, 0, q, sand)                                          # deck above the water
    c.box(w // 2, w, 1, 2, q, w, sand)                                     # pier for the fish stall
    for x in list(range(0, w, 3)) + [w - 1]:
        for z in list(range(0, w, 3)) + [w - 1]:
            if z < q or x >= w // 2:
                c.box(x, x + 1, -8, 1, z, z + 1, "sandstone")              # piles
    # Plinth with a band in the player color, stairs up the front
    px0, px1, pz1 = 1, w - 2, q - 1
    c.box(px0, px1, 2, 4, 0, pz1, cut)
    c.walls(px0, px1, 3, 4, 0, pz1, f"{col}_concrete")
    m = (px0 + px1) // 2
    c.box(m - 1, m + 2, 2, 3, pz1, pz1 + 1, "sandstone_stairs[facing=north,half=bottom,shape=straight]")
    c.box(m - 1, m + 2, 3, 4, pz1 - 1, pz1, "sandstone_stairs[facing=north,half=bottom,shape=straight]")
    for x in (m - 2, m + 2):                                               # guardian lions beside the stairs
        c.set(x, 4, pz1 - 1, chis); c.set(x, 5, pz1 - 1, "stone_brick_stairs[facing=north,half=bottom,shape=straight]")
    # House with an orange gable roof, and the prang tower on the back of the ridge
    hx0, hx1, hz1 = px0 + 1, px1 - 1, pz1 - 2
    c.room(hx0, hx1, 0, hz1, 4, 4, stone, sand, corner=relief)
    c.windows(hx0, hx1, 0, hz1, 6, b="iron_bars", step=2, sides="ew")      # stone lattice windows
    c.door(m, 4, hz1 - 1, wood="jungle")
    c.banner(m - 2, 6, hz1, col); c.banner(m + 2, 6, hz1, col)
    ridge = c.gable(hx0 - 1, hx1 + 1, 0, hz1 + 1, 8, "red_sandstone", fill=(hx0, hx1, 0, hz1, relief), axis="z")
    s, cz = 5, 2
    c.box(m - 2, m + 3, ridge - 1, ridge + 2, cz - 2, cz + 3, stone)
    c.walls(m - 2, m + 3, ridge + 1, ridge + 2, cz - 2, cz + 3, relief)
    y0, h = ridge + 2, max(7, 2 * T)
    for k in range(h):                                                     # the lotus bud: rings, narrower each tier
        r = max(0.5, (s / 2 + 0.5) * (1 - (k / h) ** 1.5) ** 0.8)
        c.cylinder(m, cz, r, y0 + k, y0 + k + 1, relief if k % 2 else stone)
    c.box(m, m + 1, y0 + h, y0 + h + 2, cz, cz + 1, "gold_block")
    # Fish stall on the pier: an awning in the player color on posts, with goods
    ax0 = w // 2 + 1
    for x in (ax0, w - 1):
        for z in (q, w - 1):
            c.box(x, x + 1, 2, 4, z, z + 1, "jungle_fence")
    c.box(ax0, w, 4, 5, q, w, f"{col}_wool")
    goods = ["barrel[facing=up]", "melon", "decorated_pot", "chest[facing=south]", "composter", "decorated_pot"]
    for x, z in ((ax0 + 1, q + 1), (ax0 + 2, q + 1), (ax0 + 1, w - 2), (1, q - 1), (w - 2, q - 1), (w - 1, 1)):
        if c.rng.random() < 0.8:
            c.set(x, 2, z, goods[int(c.rng.integers(len(goods)))])
    # Moored boat with a high prow, and the player flag on its mast
    hull(c, 0, w // 2, q + 1, 1, 1, wood="jungle")
    c.box(0, 1, 3, 5, q + 1, q + 2, "jungle_planks"); c.set(0, 5, q + 1, "gold_block")
    c.box(2, 3, 2, 6, q + 1, q + 2, "stripped_jungle_log")
    c.flag(2, 6, q + 1, col, 2)
    # Inside (#334): a trade room. Goods and a counting table at the back wall, nets and dried fish at the
    # west wall, pots at the east wall, lanterns on the barrels and one from the roof. The door way stays free.
    ix0, ix1, iz0, iz1, y = hx0 + 1, hx1 - 2, 1, hz1 - 2, 5
    back = ["barrel[facing=up]", "chest[facing=south]", "cartography_table", "chest[facing=south]", "barrel[facing=up]"]
    items = [(ix0 + k, y, iz0, b) for k, b in enumerate(back)]
    items += [(ix0, y + 1, iz0, "lantern[hanging=false]"), (ix0 + 4, y + 1, iz0, "lantern[hanging=false]"),
              (ix0, y, iz0 + 1, "loom[facing=east]"), (ix0, y, iz0 + 2, "dried_kelp_block"),
              (ix1, y, iz0 + 1, "decorated_pot"), (ix1, y, iz0 + 2, "composter")]
    c.furniture([(x, yy, z, b) for x, yy, z, b in items if ix0 <= x <= ix1 and iz0 <= z <= iz1])
    if ix1 - ix0 >= 2 and iz1 > iz0:
        hang(c, m, y + 3, iz0 + 1)


def hull(c, x0, x1, zc, y, half, wood="oak", ribs=False):
    """A ship hull along x with pointed ends; the deck is at y. ribs=True: a hull under construction."""
    c.box(x0, x1, y - 2, y - 1, zc, zc + 1, f"stripped_{wood}_log[axis=x]")          # keel
    for x in range(x0, x1):
        hw = min(half, x - x0, x1 - 1 - x)
        if ribs and x % 2:
            continue
        for z in (zc - hw, zc + hw):
            c.box(x, x + 1, y - 1, y + 1, z, z + 1, f"{wood}_planks" if not ribs else f"stripped_{wood}_log")
        if not ribs:
            c.box(x, x + 1, y - 1, y, zc - hw + 1, zc + hw, f"{wood}_planks")
            c.box(x, x + 1, y, y + 1, zc - hw + 1, zc + hw, "air")
    for x in (x0, x1 - 1):                                                            # stem and stern posts
        c.box(x, x + 1, y - 1, y + 2, zc, zc + 1, f"{wood}_planks")


def shipyard(c, w, st, col, T, ctx):
    """Shipyard: a wooden quay on piles with a workshop, a crane and a ship under construction on the slipway."""
    q = w // 3
    c.box(0, w, 1, 2, 0, q, "spruce_planks")                               # quay along the north side
    for x in range(0, w, 3):
        c.box(x, x + 1, -8, 1, 0, 1, "spruce_log"); c.box(x, x + 1, -8, 1, q - 1, q, "spruce_log")
    c.timber_room(1, max(5, w // 3), 0, q, 1, 3, st)
    c.roof(1, max(5, w // 3), 0, q, 5, st, axis="x")
    # Inside (#334): a door to the quay, a workbench, a barrel with a lantern and a plank of hull wood.
    # Outside: a timber stack on the quay for the ship.
    wx1 = max(5, w // 3) - 2
    if q >= 4:
        c.door(wx1 + 1, 2, q // 2, facing="east")
        c.furniture([(x, y, z, b) for x, y, z, b in ((2, 2, 1, "crafting_table"), (2, 2, 2, "barrel[facing=up]"),
                     (2, 3, 2, "lantern[hanging=false]"), (2, 2, 3, "stripped_spruce_log[axis=z]"),
                     (wx1, 2, 1, "barrel[facing=up]")) if z < q - 1])
    if w >= 12:
        c.box(wx1 + 3, wx1 + 6, 2, 3, q - 3, q - 1, "stripped_spruce_log[axis=x]")
        c.box(wx1 + 3, wx1 + 6, 3, 4, q - 3, q - 2, "stripped_spruce_log[axis=x]")
    hull(c, 1, w - 1, (q + w) // 2, 1, (w - q) // 2 - 1, ribs=True)
    mx, mh = w - 2, max(8, w // 2 + 4)                                     # crane over the hull
    c.box(mx, mx + 1, 2, mh, 1, 2, "stripped_spruce_log")
    c.box(mx, mx + 1, mh, mh + 1, 1, (q + w) // 2 + 1, "stripped_spruce_log[axis=z]")
    c.box(mx, mx + 1, mh - 3, mh, (q + w) // 2, (q + w) // 2 + 1, "iron_chain")
    c.set(w // 2, 2, 1, "barrel[facing=up]"); c.set(w // 2 + 1, 2, 1, "chest[facing=south]")
    c.flag(mx, mh + 1, 1, col, 2)


def port(c, w, st, col, T, ctx):
    """Port: a stone quay with bollards and goods, a warehouse and a wooden pier into the water."""
    q = w // 2
    c.box(0, w, -8, 2, 0, q, st.stone)                                     # quay wall down into the water
    c.box(0, w, 1, 2, q - 1, q, "polished_andesite")
    for x in range(1, w, 3):
        c.set(x, 2, q - 1, "stone_brick_wall")                             # bollards
    c.room(1, w // 2 + 1, 0, q - 2, 1, 4, st.plaster, st.floor, corner=st.stone)
    c.roof(1, w // 2 + 1, 0, q - 2, 5, st, axis="x")
    c.door(w // 4, 2, q - 3)
    # Inside (#334): a warehouse. Stacked barrels and chests at the back wall, sacks of grain at the west wall,
    # a counting table with a lantern at the east wall, a lantern from the roof.
    ix0, ix1, iz0, iz1 = 2, w // 2 - 1, 1, q - 4
    items = [(ix0, 2, iz0, "barrel[facing=up]"), (ix0, 3, iz0, "barrel[facing=up]"), (ix0 + 1, 2, iz0, "barrel[facing=up]"),
             (ix0 + 2, 2, iz0, "chest[facing=south]"), (ix1 - 1, 2, iz0, "chest[facing=south]"),
             (ix1, 2, iz0, "barrel[facing=up]"), (ix1, 3, iz0, "barrel[facing=up]"),
             (ix0, 2, iz0 + 1, "hay_block"), (ix0, 2, iz0 + 2, "hay_block"), (ix0, 3, iz0 + 1, "hay_block"),
             (ix1, 2, iz0 + 1, "cartography_table"), (ix1, 3, iz0 + 1, "lantern[hanging=false]"),
             (ix1, 2, iz0 + 2, "barrel[facing=up]")]
    c.furniture([(x, y, z, b) for x, y, z, b in items if ix0 <= x <= ix1 and iz0 <= z <= iz1])
    if ix1 - ix0 >= 2 and iz1 > iz0:
        hang(c, (ix0 + ix1) // 2 + 1, 4, iz0 + 1)
    m = w * 3 // 4                                                         # pier
    c.box(m - 1, m + 2, 1, 2, q, w, "spruce_planks")
    for z in range(q + 1, w, 3):
        c.box(m - 1, m, -8, 1, z, z + 1, "spruce_log"); c.box(m + 1, m + 2, -8, 1, z, z + 1, "spruce_log")
    c.set(w - 2, 2, 1, "barrel[facing=up]"); c.set(w - 3, 2, 1, "chest[facing=south]")
    c.set(w - 2, 2, 2, "barrel[facing=up]")
    c.flag(m + 1, 2, w - 1, col, 2)


def mole(c, w, st, col, T, ctx, built=True):
    """Mole (siege of Tyre): a causeway of rubble into the sea. Unfinished: a lower fill and a wooden frame."""
    top = 1 if built else 0
    for x in range(w):
        for z in range(w):
            c.box(x, x + 1, -10, top, z, z + 1, ["cobblestone", "stone", "andesite", "gravel"][int(c.rng.integers(4))])
    c.box(0, w, top, top + 1, 0, w, "gravel" if built else "air")
    c.box(0, w, top, top + 1, 1, w - 1, "coarse_dirt" if built else "air")
    if not built:
        for x in range(0, w, 3):
            for z in (0, w - 1):
                c.box(x, x + 1, 0, 3, z, z + 1, "spruce_log")
        c.box(0, w, 2, 3, 0, 1, "spruce_log[axis=x]"); c.box(0, w, 2, 3, w - 1, w, "spruce_log[axis=x]")
        c.set(w // 2, 1, w // 2, "barrel[facing=up]")


CHAIN_DIRECTION = {"NORTHWEST_TO_SOUTHEAST": (1, 0), "SOUTHWEST_TO_NORTHEAST": (0, 1),
                   "WEST_TO_EAST": (1, -1), "NORTH_TO_SOUTH": (1, 1)}


def harbor_chain(c, w, st, col, T, ctx):
    """Harbor chain on the water. It runs from edge to edge of the tile, so pieces next to each other connect.
    AoE2 screen directions: map x runs to the south-east and map y to the south-west on the screen."""
    dx, dz = next(d for k, d in CHAIN_DIRECTION.items() if ctx["name"].endswith(k))
    if dz == 0:
        c.box(0, w, 0, 1, w // 2, w // 2 + 1, "iron_chain[axis=x]")
    elif dx == 0:
        c.box(w // 2, w // 2 + 1, 0, 1, 0, w, "iron_chain[axis=z]")
    else:
        for i in range(w):                                                 # diagonal: a staircase of links
            z = i if dz > 0 else w - 1 - i
            c.set(i, 0, z, "iron_chain[axis=x]")
            if i < w - 1:
                c.set(i + 1, 0, z, "iron_chain[axis=z]")
    c.set(w // 2, 0, w // 2, "barrel[facing=up]")                          # float in the middle


def flagship(c, w, st, col, T, ctx):
    """Flagship of Nearchos: a large galley with a mast, a square sail in the player color and oars."""
    zc, half = w // 2, max(2, w // 4)
    hull(c, 0, w, zc, 1, half)
    c.box(1, 2, 2, 3, zc - 1, zc + 2, "oak_planks"); c.box(w - 2, w - 1, 2, 3, zc - 1, zc + 2, "oak_planks")
    for x in range(2, w - 2, 2):                                           # oars
        c.set(x, 0, zc - half - 1, "oak_fence"); c.set(x, 0, zc + half + 1, "oak_fence")
    m, mh = w // 2, max(9, w)
    c.box(m, m + 1, 1, mh, zc, zc + 1, "stripped_oak_log")
    c.box(m, m + 1, mh - 1, mh, zc - half, zc + half + 1, "stripped_oak_log[axis=z]")
    c.box(m, m + 1, mh - 5, mh - 1, zc - half + 1, zc + half, f"{col}_wool")
    c.box(m, m + 1, mh - 5, mh - 1, zc, zc + 1, "stripped_oak_log")
    c.flag(m, mh, zc, col, 2)
    # Deck (#500): the hull has one level above the water, so the cargo stands on the open deck.
    # Rowing benches at the oars, cargo (barrels, a chest, sacks) on both sides of the mast and a lantern.
    items = []
    for x in range(2, w - 2, 2):
        hw = min(half, x, w - 1 - x)
        if hw >= 2:
            items += [(x, 1, zc - hw + 1, "spruce_slab[type=bottom]"), (x, 1, zc + hw - 1, "spruce_slab[type=bottom]")]
    items += [(m - 1, 1, zc, "barrel[facing=up]"), (m - 2, 1, zc, "barrel[facing=up]"),
              (m + 1, 1, zc, "chest[facing=west,type=single,waterlogged=false]"), (m + 2, 1, zc, "hay_block[axis=x]"),
              (m - 1, 1, zc - 1, "barrel[facing=up]"), (m + 1, 1, zc + 1, "hay_block[axis=x]")]
    c.furniture(items)
    if c.get(m - 2, 1, zc) == c.id("barrel[facing=up]"):                 # above the deck the cells are empty, not air
        c.set(m - 2, 2, zc, "lantern[hanging=false]")


def helepolis(c, w, st, col, T, ctx):
    """Helepolis: a very tall siege tower on wheels, with hides on the walls and shutters on the front."""
    for x in (0, w - 1):                                                   # wheels
        for z in (1, w - 2):
            c.box(x, x + 1, 0, 2, z - 1, z + 1, "stripped_spruce_log[axis=x]")
    y, a, b, k = 1, 1, w - 1, 0
    while b - a >= 3:
        c.walls(a, b, y, y + 3, a, b, "spruce_planks")
        c.box(a, a + 1, y, y + 3, a, a + 1, "spruce_log"); c.box(b - 1, b, y, y + 3, a, a + 1, "spruce_log")
        c.box(a, a + 1, y, y + 3, b - 1, b, "spruce_log"); c.box(b - 1, b, y, y + 3, b - 1, b, "spruce_log")
        if k < 2:
            c.walls(a, b, y, y + 1, a, b, "brown_wool")                     # hides against fire
        m = (a + b) // 2
        c.set(m, y + 1, b - 1, "spruce_trapdoor[facing=south,half=top,open=true]")
        c.box(a, b, y + 3, y + 4, a, b, "spruce_planks")
        inner = lambda x, z: a < x < b - 1 and a < z < b - 1
        c.box(m, m + 1, y, y + 4, m, m + 1, "spruce_log")                 # a mast through all floors with a ladder (#501)
        if inner(m, m - 1):
            c.box(m, m + 1, y, y + 4, m - 1, m, "ladder[facing=north]")
        stuff = [(a + 1, y + 2, b - 2, "lantern[hanging=true]"), (b - 2, y + 2, a + 1, "lantern[hanging=true]"),
                 (b - 2, y, b - 2, "barrel[facing=up]"), (a + 1, y, a + 1, "barrel[facing=up]")]   # arrows
        if k == 0:
            stuff += [(m + 1, y, m, "grindstone[face=floor,facing=east]"), (a + 1, y, b - 2, "chest[facing=east]")]
        for x, yy, z, s in stuff:
            if inner(x, z) and c.get(x, yy, z) == -1:
                c.set(x, yy, z, s)
        y, k = y + 4, k + 1
        if k % 2 == 0:
            a, b = a + 1, b - 1
    c.crenels(a, b, a, b, y, "spruce_fence")
    c.flag((a + b) // 2, y, (a + b) // 2, col, 2)


def tower(c, w, st, col, T, ctx, kind="watch"):
    """Slim shaft, a door, bands in the player color and an overhanging lookout with the roof of the set (#76)."""
    stone, mid, cc = st.stone, w // 2, (w - 1) / 2
    hb = max({"watch": 3 * T, "guard": 3 * T + 2, "bombard": 3 * T + 2, "keep": 3 * T + 4}.get(kind, 3 * T), 8)
    high = kind != "watch"
    rnd = st.domes and not st.eaves and not st.torons                     # Middle Eastern towers are round
    c.box(0, w, 0, 1, 0, w, st.stone2)
    if rnd:
        c.cylinder(cc, cc, w / 2 - 0.2, 1, hb, stone)
    else:
        c.box(0, w, 1, hb, 0, w, stone)
    for y in range(4, hb - 1, 3):                                         # arrow slits
        c.set(mid, y, w - 1, "iron_bars"); c.set(w - 1, y, mid, "iron_bars"); c.set(0, y, mid, "iron_bars")
    band = [hb - 2] + ([hb // 2] if high else [])
    for y in band:                                                        # bands in the player color
        if rnd:
            c.cylinder(cc, cc, w / 2 - 0.2, y, y + 1, f"{col}_wool", hollow=True)
        else:
            c.walls(0, w, y, y + 1, 0, w, f"{col}_wool")
    c.door(mid - (w > 3), 1, w - 1, wood=st.wood.removesuffix("_planks"))
    stone_top = st.shape == "flat" and not (st.torons and not high)
    lx, lz, bx = w - 2, 1, 1                                              # ladder and barrel cells (x, z, x)
    if w >= 4 and rnd:                                                    # round shaft: the cells with wall all round (#3096)
        m, X, Z = c.disc_mask(cc, cc, w / 2 - 0.2)
        m = m & np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1)
        c._fill_mask(m, 1, hb - 1, "air")
        lz = int(Z[m].min())
        lx, bx = int(X[m & (Z == lz)].max()), int(X[m & (Z == lz)].min())
        dx = mid - (w > 3)
        c.box(dx, dx + 1, 1, 3, int(Z[m & (X == dx)].max()) + 1, w - 1, "air")   # the way from the door
    elif w >= 4:                                                          # hollow shaft, a ladder to the lookout (#256)
        c.box(1, w - 1, 1, hb - 1, 1, w - 1, "air")
    if w >= 4:
        c.set(bx, 1, lz, "barrel[facing=up]")
        c.set(bx, hb - 2, lz, "lantern[hanging=true]")
    if stone_top:                                                         # stone lookout with merlons
        if rnd:
            c.cylinder(cc, cc, w / 2 + 0.8, hb, hb + 2, stone)
            c.cylinder(cc, cc, w / 2 - 0.2, hb + 1, hb + 2, st.wood)
            c.cylinder(cc, cc, w / 2 + 0.8, hb + 2, hb + 3, st.merlon or stone, hollow=True)
            c.cylinder(cc, cc, w / 2 - 0.2, hb + 2, hb + 3, "air")
        else:
            c.box(-1, w + 1, hb, hb + 2, -1, w + 1, stone)
            c.box(0, w, hb + 1, hb + 2, 0, w, st.wood)
            c.crenels(-1, w + 1, -1, w + 1, hb + 2, st.merlon or stone)
        for x, z in ((mid, -1), (mid, w), (-1, mid), (w, mid)):          # openings of the lookout
            c.set(x, hb + 1, z, "iron_bars")
        top = hb + 2
        if st.eaves:                                                      # chhajja: a sloped overhang
            sl = family(st.roof)[1]
            c.walls(-2, w + 2, hb + 1, hb + 2, -2, w + 2, f"{sl}[type=top]")
        if kind == "keep" or (st.eaves and high):            # a dome on the large towers
            top = c.dome(cc, cc, max(1.2, w / 2 - 0.5), hb + 2, st.dome)
        else:
            c.flag(mid, hb + 2, mid, col, 3)
            top = -1
    else:                                                                 # wooden lookout on posts, roof over it
        c.box(-1, w + 1, hb, hb + 1, -1, w + 1, st.wood)
        c.walls(-1, w + 1, hb + 1, hb + 2, -1, w + 1, "spruce_fence")
        for x in (-1, w):
            for z in (-1, w):
                c.box(x, x + 1, hb + 1, hb + 3, z, z + 1, st.timber)
        if st.shape == "flat":                                            # African: thatch
            top = c.spire(-2, w + 2, -2, w + 2, hb + 3, "hay_block", steep=1, tip=None)
        elif st.wonder == "pyramid":                                      # Mesoamerican: stepped stone crown
            c.box(-1, w + 1, hb + 3, hb + 4, -1, w + 1, st.stone2)
            top = c.spire(0, w, 0, w, hb + 4, stone, steep=1, tip=None)
        elif st.wonder == "temple":                                       # Southeast Asian: stepped spire, gold tip
            c.hip(-2, w + 2, -2, w + 2, hb + 3, st.roof, layers=1, flare=True)
            top = c.spire(0, w, 0, w, hb + 4, stone, steep=1, tip="gold_block")
        elif st.shape == "gable":                                         # European: tall pointed roof
            top = c.spire(-2, w + 2, -2, w + 2, hb + 3, family(st.roof)[2], steep=2, tip="lightning_rod")
        else:
            top = c.hip(-2, w + 2, -2, w + 2, hb + 3, st.roof, flare=st.shape == "asian")
    if top >= 0:
        c.flag(mid, top + 1, mid, col, 2)
    if w >= 4:                                                            # through the lookout floor
        c.box(lx, lx + 1, 1, hb + stone_top + 1, lz, lz + 1, "ladder[facing=south]")
    if kind == "bombard":                                                 # cannon barrels out of the lookout
        for x, z, ax in ((mid, w, "z"), (mid, w + 1, "z"), (w, mid, "x"), (w + 1, mid, "x"),
                         (mid, -1, "z"), (mid, -2, "z"), (-1, mid, "x"), (-2, mid, "x")):
            c.set(x, hb + 1, z, f"polished_basalt[axis={ax}]")
    c.banner(mid, hb - 4, w, col)


def donjon(c, w, st, col, T, ctx):
    """Donjon (Sicilians): a tall square keep on a low crenellated base, a flat top with merlons and a band in the
    player color, a wooden hoarding, and a corner stair turret with the roof of the set."""
    stone, mid = st.stone, w // 2
    wood = st.wood.removesuffix("_planks")
    wood = wood if wood in WOODS else "spruce"
    hk = max(3 * T + 4, 9)                                                 # top of the keep walls
    c.box(0, w, 0, 1, 0, w, st.stone2)
    c.box(0, w, 1, 3, 0, w, st.stone2)                                     # base (talus) with a walkway
    c.crenels(0, w, 0, w, 3, st.merlon or st.stone2)
    c.box(1, w - 1, 1, hk, 1, w - 1, stone)                                # keep
    c.box(mid - (w > 3), mid - (w > 3) + 1, 1, 3, w - 1, w, "air")         # gate in the base
    c.door(mid - (w > 3), 1, w - 2, wood=wood)
    c.banner(mid - (w > 3), 5, w - 1, col)                                 # coat of arms over the gate
    for y in range(5, hk - 2, 3):                                          # arrow slits
        for x, z in ((mid, 1), (1, mid), (w - 2, mid)):
            c.set(x, y, z, "iron_bars")
        if w > 4:
            c.set(mid + 1, y, w - 2, "iron_bars")
    c.walls(1, w - 1, hk - 1, hk, 1, w - 1, f"{col}_wool")                 # band in the player color
    c.crenels(1, w - 1, 1, w - 1, hk, st.merlon or stone)
    c.box(2, w - 2, hk - 1, hk, 2, w - 2, st.floor)                        # roof terrace with goods
    c.set(2, hk, w - 3, "barrel[facing=up]")
    if w >= 8:                                                             # rooms in the keep (#330)
        c.box(2, w - 2, 1, hk - 1, 2, w - 2, "air")
        floors = [0, *range(6, hk - 4, 4)]                                 # between the arrow slits
        for f in floors[1:]:
            c.box(2, w - 2, f, f + 1, 2, w - 2, st.wood)
        keep_inside(c, 2, w - 2, floors, hk - 1, st, col)
    if w >= 6:
        x0, x1, z0, z1 = w - 3, w, 0, 3                                   # stair turret on the north-east corner
        ht = hk + 4
        c.box(x0, x1, 1, ht, z0, z1, stone)
        c.walls(x0, x1, hk - 4, hk - 3, z0, z1, f"{col}_wool")
        for y in range(6, ht - 3, 4):
            c.set(x1 - 1, y, z0 + 1, "iron_bars")
        if st.shape in ("gable", "hip"):                                   # the tiled hip roof of the game model
            top = c.hip(x0 - 1, x1 + 1, z0 - 1, z1 + 1, ht - 1, "brick")
        else:
            top = c.roof(x0, x1, z0, z1, ht, st)
        c.flag(x0 + 1, top + 1, z0 + 1, col, 2)
        c.box(2, min(5, w - 2), hk - 3, hk - 2, w - 1, w, f"{wood}_slab[type=top]")   # wooden hoarding
        c.box(2, min(5, w - 2), hk - 2, hk - 1, w - 1, w, f"{wood}_fence")
    else:
        c.flag(mid, hk, mid, col, 2)


def feitoria(c, w, st, col, T, ctx):
    """Feitoria (Portuguese): a walled trade post. A tall main tower with corner turrets at the back, a small
    tower on the front corner, warehouses with tiled roofs, a yard with goods and a gate in the south wall."""
    stone, pl, mid = st.stone, st.plaster, w // 2
    tiled = st.shape != "flat"                                             # terracotta roofs, as in the game

    def roof(x0, x1, z0, z1, y, axis=None):
        if not tiled:
            return c.roof(x0, x1, z0, z1, y, st)
        if axis:
            return c.gable(x0 - 1, x1 + 1, z0 - 1, z1 + 1, y - 1, "brick", fill=(x0, x1, z0, z1, pl), axis=axis)
        return c.hip(x0 - 1, x1 + 1, z0 - 1, z1 + 1, y - 1, "brick")

    c.box(0, w, 0, 1, 0, w, st.stone2)
    c.walls(0, w, 1, 4, 0, w, stone)                                       # curtain wall
    c.walls(0, w, 1, 2, 0, w, f"{col}_concrete")                           # painted band at the foot
    c.box(mid - 1, mid + 1, 1, 3, w - 1, w, "air")                         # gate
    c.box(mid - 1, mid + 1, 3, 4, w - 1, w, "chiseled_stone_bricks")
    d = max(4, w // 3)                                                     # depth of the buildings
    c.room(1, mid - 2, 1, d, 0, 4, pl, st.floor, corner=stone)
    c.windows(1, mid - 2, 1, d, 3, step=3, sides="s")
    roof(1, mid - 2, 1, d, 5, axis="x")                                    # warehouse on the north side
    c.room(w - d, w - 1, d, w - 4, 0, 4, pl, st.floor, corner=stone)
    c.windows(w - d, w - 1, d, w - 4, 3, step=3, sides="w")
    c.door(w - d, 1, (d + w - 4) // 2, facing="west")
    roof(w - d, w - 1, d, w - 4, 5, axis="z")                              # warehouse on the east side
    # Main tower with corner turrets
    x0, x1, z0, z1 = mid - 2, mid + 3, 0, 5
    ht = max(10, 3 * T + 2)
    c.room(x0, x1, z0, z1, 0, ht, stone, st.floor)
    c.walls(x0, x1, ht - 1, ht, z0, z1, f"{col}_concrete")
    for y in range(4, ht - 2, 3):
        c.set(mid, y, z1 - 1, "glass_pane"); c.set(x0, y, (z0 + z1) // 2, "glass_pane")
    wood = st.wood.removesuffix("_planks")
    c.door(mid, 1, z1 - 1, wood=wood if wood in WOODS else "spruce")
    top = roof(x0, x1, z0, z1, ht + 1)
    for x in (x0 - 1, x1):
        for z in (z0 - 1 if z0 else z0, z1):
            c.box(x, x + 1, ht - 1, ht + 1, z, z + 1, stone)
            c.set(x, ht + 1, z, "smooth_quartz"); c.set(x, ht + 2, z, "lightning_rod")
    c.flag(mid, top + 1, (z0 + z1) // 2, col, 2)
    # Small tower on the south-west corner
    sx1, sz0 = 5, w - 5
    hs = max(7, 2 * T)
    c.room(0, sx1, sz0, w, 0, hs, stone, st.floor)
    c.windows(0, sx1, sz0, w, hs - 2, step=2)
    c.banner(sx1, 5, sz0 + 2, col, facing="east")
    roof(0, sx1, sz0, w, hs + 1)
    # Goods in the yard
    goods = ["barrel[facing=up]", "chest[facing=south]", "hay_block", "gold_block", "barrel[facing=up]", "composter"]
    for x, z in ((mid - 2, d + 2), (mid - 1, d + 2), (mid + 1, d + 3), (6, w - 3), (7, w - 3), (mid + 2, w - 3)):
        if c.rng.random() < 0.8:
            c.set(x, 1, z, goods[int(c.rng.integers(len(goods)))])
    # Inside: crates and sacks in the warehouses and the small tower, the counting room in the main tower
    stock = ["barrel[facing=up]", "chest[facing=south]", "brown_wool", "white_wool", "hay_block", "barrel[facing=up]"]
    rooms = [(2, mid - 3, 2, d - 1, 4), (w - d + 1, w - 2, d + 1, w - 5, 4), (1, sx1 - 1, sz0 + 1, w - 1, hs)]
    items = []
    for rx0, rx1, rz0, rz1, ry in rooms:                                   # inside cells rx0..rx1-1, rz0..rz1-1
        for x in range(rx0, rx1):
            for z in range(rz0, rz1):
                if (x in (rx0, rx1 - 1) or z == rz0) and c.rng.random() < 0.7:
                    items += [(x, 1, z, stock[int(c.rng.integers(len(stock)))])]
                    if c.rng.random() < 0.4:
                        items += [(x, 2, z, stock[int(c.rng.integers(len(stock)))])]
        items += [((rx0 + rx1) // 2, ry, (rz0 + rz1) // 2, "lantern[hanging=true]")]        # under the ceiling
    items += [(x0 + 1, 1, z0 + 1, "cartography_table"), (x0 + 1, 2, z0 + 1, "lantern[hanging=false]"),
              (x0 + 2, 1, z0 + 1, "lectern[facing=south,has_book=true,powered=false]"), (x1 - 2, 1, z0 + 1, "chest[facing=south]"),
              (x0 + 1, 1, z0 + 2, stair(f"{wood if wood in WOODS else 'spruce'}_stairs", "south")), (x1 - 2, 1, z0 + 2, "barrel[facing=up]")]
    c.furniture(items)


def outpost(c, w, st, col, T, ctx):
    """Like the game (#485): a lookout hut on four stilts with rails as braces, a ladder at the front, a low wall in
    the player color and a canvas roof with a valance in the player color. The fortified outpost stands on stone."""
    hp, y0 = 2 * T + 2, 1
    if "FORTIFIED" in ctx.get("name", ""):
        c.box(0, w, 1, 3, 0, w, st.stone2)
        y0 = 3
    for x in (0, w - 1):
        for z in (0, w - 1):
            c.box(x, x + 1, y0, hp + 4, z, z + 1, st.timber)          # stilts, up to the roof
    for y in (y0 + 1, (y0 + hp) // 2 + 1):
        c.walls(0, w, y, y + 1, 0, w, "spruce_fence")                 # braces between the stilts
        for x in (0, w - 1):
            for z in (0, w - 1):
                c.set(x, y, z, st.timber)
    c.box(0, w, hp, hp + 1, 0, w, st.wood)
    c.walls(0, w, hp + 1, hp + 2, 0, w, f"{col}_wool")                # the hut: a band, cloth, then open
    c.walls(0, w, hp + 2, hp + 3, 0, w, "white_wool")
    for x in (0, w - 1):
        for z in (0, w - 1):
            c.box(x, x + 1, hp + 1, hp + 3, z, z + 1, st.timber)
    c.box(-1, w + 1, hp + 4, hp + 5, -1, w + 1, f"{col}_wool")        # the valance of the roof
    c.box(0, w, hp + 4, hp + 5, 0, w, "white_wool")                   # canvas
    c.box(1, w - 1, hp + 5, hp + 6, 1, w - 1, "white_wool")
    if w >= 3:
        x = w // 2
        c.box(x, x + 1, y0, hp, w - 2, w - 1, st.timber)              # the ladder leans on a pole
        c.box(x, x + 1, y0, hp + 1, w - 1, w, "ladder[facing=south]")
        c.box(x, x + 1, hp + 1, hp + 4, w - 1, w, "air")              # the way in
        c.set(x, hp + 1, w - 2, "air")
        c.set(1, hp + 1, 1, "campfire[lit=true,signal_fire=false]")   # the signal fire
    c.flag(w // 2, hp + 6 - (w < 3), w // 2, col, 1)


def wall_shape(w, ctx, every=3):
    """(x0, x1, z0, z1) of the wall body on a wall tile, and whether the tile has a pillar: wall ends, corners,
    crossings and every 3rd tile of a straight line get a pillar of the full tile, the others a thinner wall."""
    (n, s, wst, e), (gx, gz) = ctx["neighbours"], ctx["origin"]
    t = w // 4
    if (n or s) and not (wst or e):
        return (t, w - t, 0, w), (gz // w) % every == 0 or not (n and s)
    if (wst or e) and not (n or s):
        return (0, w, t, w - t), (gx // w) % every == 0 or not (wst and e)
    return (0, w, 0, w), True


def wall_segment(c, w, st, col, T, ctx):
    """One wall tile. ctx: name, neighbours (N, S, W, E booleans), global block offset.
    Like the game: a wall between square pillars that are higher and wider, with a band in the player color
    at the base of the pillars. Palisades: a row of pointed stakes of two heights."""
    name, (gx, gz) = ctx["name"], ctx["origin"]
    if "FENCE" in name:
        return fence(c, w, st, col, T, ctx)
    (x0, x1, z0, z1), pillar = wall_shape(w, ctx)
    if "PALISADE" in name:
        h = T + (2 if "FORTIFIED" in name else 1)
        if pillar:                                    # a square palisade tower
            x0, x1, z0, z1 = 0, w, 0, w
            h += 1
        if "FORTIFIED" in name:
            c.box(x0, x1, 1, 2, z0, z1, st.stone2)    # stone foundation
        for x in range(x0, x1):
            for z in range(z0, z1):
                top = h - (x + gx + 2 * (z + gz)) % 3 // 2
                c.box(x, x + 1, 1 + ("FORTIFIED" in name), top + 1, z, z + 1, "spruce_log[axis=y]")
                c.set(x, top + 1, z, "spruce_fence")  # the pointed tip of the stake
        if pillar and w >= 4:
            c.box(x0 + 1, x1 - 1, h - 1, h + 2, z0 + 1, z1 - 1, "air")
            c.box(x0 + 1, x1 - 1, h - 1, h, z0 + 1, z1 - 1, "spruce_planks")
        wall_banners(c, w, ctx, h - 1, col, (x0, x1, z0, z1))
        return
    fort = any(k in name for k in ("FORTIFIED", "CITY", "FORT_", "SEA_WALL"))
    h = T + (3 if fort else 2)
    cap = st.accent if fort else (st.merlon or st.stone)
    c.box(x0, x1, 1, h + 1, z0, z1, st.stone)
    if fort:
        c.box(x0, x1, h, h + 1, z0, z1, st.accent)
    for x in range(x0, x1):                           # merlons on the two long sides of the walkway
        for z in range(z0, z1):
            if (x + gx + z + gz) % 2 == 0 and (z in (z0, z1 - 1) if x1 - x0 == w else x in (x0, x1 - 1)):
                c.set(x, h + 1, z, cap)
    if pillar:
        ph = h + 2
        c.box(0, w, 1, ph + 1, 0, w, st.stone)
        c.walls(0, w, 2, 3, 0, w, f"{col}_wool")      # the band in the player color
        c.box(0, w, ph, ph + 1, 0, w, st.accent)
        if w >= 3:
            c.crenels(0, w, 0, w, ph + 1, cap, gx, gz)
    wall_banners(c, w, ctx, h - 1, col, (0, w, 0, w) if pillar else (x0, x1, z0, z1))


def fence(c, w, st, col, T, ctx):
    """A low wooden fence through the middle of the tile, connected to the fences and walls next to it."""
    n, s_, wst, e = ctx["neighbours"]
    if not any((n, s_, wst, e)):
        n = s_ = True
    m = w // 2
    def post(conn):
        return "oak_fence[" + ",".join(f"{d}={'true' if d in conn else 'false'}" for d in ("east", "north", "south", "west")) + "]"
    if n:
        c.box(m, m + 1, 1, 2, 0, m, post({"north", "south"}))
    if s_:
        c.box(m, m + 1, 1, 2, m + 1, w, post({"north", "south"}))
    if wst:
        c.box(0, m, 1, 2, m, m + 1, post({"east", "west"}))
    if e:
        c.box(m + 1, w, 1, 2, m, m + 1, post({"east", "west"}))
    c.set(m, 1, m, post({d for d, v in (("north", n), ("south", s_), ("west", wst), ("east", e)) if v}))


BARRICADE_DEBRIS = ["cobblestone", "andesite", "mossy_cobblestone", "spruce_log[axis=x]", "spruce_log[axis=z]",
                    "stripped_spruce_log[axis=x]", "stripped_spruce_log[axis=z]", "spruce_planks", "spruce_slab[type=bottom]"]
BARRICADE_TOP = ["mangrove_roots", "mangrove_roots", "spruce_fence", "oak_leaves[persistent=true]", "barrel[facing=up]",
                 "decorated_pot[facing=south,cracked=false]", "stone_button[face=floor,facing=north]"]


def barricade(c, w, st, col, T, ctx):
    """A barricade like the game: a low heap of debris (stones, logs, planks, bare branches, crates, pots and ivy).
    BARRICADE_A is a round heap; B, C and D are long heaps along x and along the two diagonals."""
    k = "ABCD".find(ctx.get("name", "BARRICADE_A")[-1])
    x, z = np.mgrid[0:w, 0:w] - (w - 1) / 2
    u, v = [(x, z), (x, z), (x + z, z - x), (x - z, x + z)][max(k, 0)]
    if k >= 2:
        u, v = u / 1.6, v / 1.6
    rx, rz = (w / 2, w / 2) if k <= 0 else (w / 2 + .5, w / 3)
    d = (u / rx) ** 2 + (v / rz) ** 2 + c.rng.uniform(-.2, .2, (w, w))       # a ragged edge
    h = (d < 1).astype(int) + (d < .45)                                       # 1 block at the edge, 2 in the middle
    pick = c.rng.integers(0, len(BARRICADE_DEBRIS), (w, w, 2))
    top = c.rng.integers(0, 3 * len(BARRICADE_TOP), (w, w))                   # one top cell in three gets a part
    for i, j in zip(*np.nonzero(h)):
        for y in range(h[i, j]):
            c.set(i, y + 1, j, BARRICADE_DEBRIS[pick[i, j, y]])
        if top[i, j] < len(BARRICADE_TOP):
            c.set(i, h[i, j] + 1, j, BARRICADE_TOP[top[i, j]])


def wall_banners(c, w, ctx, y, col, body=None, every=4):
    """A banner in the player color on the open sides of every 4th wall tile. It hangs on the face of the wall
    body (x0, x1, z0, z1), so that it does not float in front of a thin wall."""
    gx, gz = ctx["origin"]
    if (gx // w + gz // w) % every:
        return
    n, s, wst, e = ctx["neighbours"]
    m = w // 2
    x0, x1, z0, z1 = body or (0, w, 0, w)
    if not s: c.banner(m, y, z1, col, "south")
    if not n: c.banner(m, y, z0 - 1, col, "north")
    if not e: c.banner(x1, y, m, col, "east")
    if not wst: c.banner(x0 - 1, y, m, col, "west")


def gate(c, w, st, col, T, ctx):
    """Gate along the x axis: towers at both ends and an opening in the middle (w = 4 tiles)."""
    name = ctx["name"]
    if ctx.get("diag"):
        return diagonal_gate(c, w, st, col, T, ctx)
    z0, z1 = 0, T
    if "PALISADE" in name:
        h = T + 1
        for x in range(w):
            for z in range(z0, z1):
                top = h + (2 if x < T or x >= w - T else 0) - (x + 2 * z) % 3 // 2
                c.box(x, x + 1, 1, top + 1, z, z + 1, "spruce_log[axis=y]")
                c.set(x, top + 1, z, "spruce_fence")
        c.box(T, w - T, 1, 4, z0, z1, "air")
        c.box(T, w - T, 4, h + 1, z0, z1, "stripped_spruce_log[axis=x]")
        c.box(T, w - T, 4, 5, z0, z0 + 1, "iron_bars")                     # the raised grille
        c.flag(T - 1, h + 3, z1 // 2, col, 2); c.flag(w - T, h + 3, z1 // 2, col, 2)
        return
    fort = any(k in name for k in ("FORTIFIED", "CITY", "FORT_"))
    h = T + (3 if fort else 2)
    th = h + 3
    cap = st.accent if fort else (st.merlon or st.stone)
    c.box(0, w, 1, h + 1, z0, z1, st.stone)
    c.box(T, w - T, 1, 5, z0, z1, "air")
    c.box(T, w - T, 4, 5, z0, z0 + 1, "iron_bars")                         # the raised portcullis
    c.box(T, w - T, 4, 5, z1 - 1, z1, "iron_bars")
    c.crenels(T, w - T, z0, z1, h + 1, cap)
    for x0 in (0, w - T):                                                   # the gate towers
        c.box(x0, x0 + T, 1, th, z0, z1, st.stone)
        c.walls(x0, x0 + T, 2, 3, z0, z1, f"{col}_wool")
        c.box(x0, x0 + T, th - 1, th, z0, z1, st.accent)
        c.crenels(x0, x0 + T, z0, z1, th, cap)
        c.flag(x0 + T // 2, th, z1 // 2, col, 2)
    c.banner(T // 2, h, z1, col); c.banner(w - T + T // 2, h, z1, col)


def diagonal_gate(c, w, st, col, T, ctx):
    """Gate on the diagonal x = z (w = 3 tiles): a band of wall, a tower on each end tile and an opening
    in the middle tile. Units go through it in the direction (+1, -1)."""
    palisade = "PALISADE" in ctx["name"]
    fort = any(k in ctx["name"] for k in ("FORTIFIED", "CITY", "FORT_"))
    h = T + 1 if palisade else T + (3 if fort else 2)
    mat = "spruce_log" if palisade else st.stone
    r = T // 2
    for x in range(w):
        for z in range(w):
            v, u = x - z, (x + z) / 2
            if abs(v) > r:
                continue
            end = u < T * 0.75 or u >= w - T * 0.75
            top = h + (0 if palisade or not end else 3)
            c.box(x, x + 1, 1, top + 1, z, z + 1, mat)
            if not end and T <= u < w - T:
                c.box(x, x + 1, 1, 4, z, z + 1, "air")                   # the opening
            if not palisade and abs(v) == r and x % 2 == 0:
                c.set(x, top + 1, z, st.merlon or st.stone)
    if palisade:
        c.flag(T // 2, h + 1, T // 2, col, 2); c.flag(w - 1 - T // 2, h + 1, w - 1 - T // 2, col, 2)
    else:
        c.flag(T // 3, h + 4, T // 3, col, 2); c.flag(w - 1 - T // 3, h + 4, w - 1 - T // 3, col, 2)


def farm(c, w, st, col, T, ctx):
    pass   # drawn directly on the terrain (see place_building)


def generic(c, w, st, col, T, ctx):
    m = inset(w)
    hw = 3 + w // 6
    c.timber_room(m, w - m, m, w - m, 0, hw, st, low_stone=1)
    c.windows(m, w - m, m, w - m, 2)
    top = c.roof(m, w - m, m, w - m, hw + 1, st)
    c.door(w // 2, 1, w - m - 1)
    c.flag(w // 2, top + 1, w // 2, col, 2)
    # A store room: barrels in the back corners, then a chest, a table with a lantern and a rug (no bed).
    c.furniture([(x, 1, m + 1, "barrel[facing=up,open=false]") for x in (m + 1, w - m - 2)])
    furnish(c, m + 1, w - m - 1, m + 1, w - m - 1, 1, st, col, door=w // 2, bed=False)


# --------------------------------------------------------------------------------------------
# Wonders (5x5 tiles), one design per architecture group
# --------------------------------------------------------------------------------------------
def vertical_disc(c, cx, cy, z, r, blocks):
    for dx in range(-int(r) - 1, int(r) + 2):
        for dy in range(-int(r) - 1, int(r) + 2):
            if dx * dx + dy * dy <= r * r + 0.5:
                c.set(cx + dx, cy + dy, z, blocks[(abs(dx) + abs(dy)) % len(blocks)])


def cathedral(c, w, st, col, T, ctx):
    """Gothic cathedral: nave and transept, a tall crossing tower, two front towers, a rose window and a portal.
    Western sets get green copper roofs, the Mediterranean set (brick roofs) a dome and striped marble walls."""
    stone = "stone_bricks" if "mossy" in st.stone else st.stone
    roof = st.roof if st.shape in ("gable", "hip") else "deepslate_tile"
    roof = "weathered_cut_copper" if roof in WOODS else roof               # wood roofs: copper, as in the game
    southern = st.shape == "hip"
    c.box(0, w, 0, 1, 0, w, st.stone2)
    nw = max(5, (w * 2) // 5) | 1
    x0, x1 = (w - nw) // 2, (w - nw) // 2 + nw
    mid = (x0 + x1 - 1) // 2          # the axis of the nave
    hn = max(6, w // 2)
    t = 3 if w < 18 else 4
    # Nave and transept
    c.room(x0, x1, 1, w, 0, hn, stone, st.floor)
    tz0, tz1 = w // 5, w // 5 + nw
    c.room(1, w - 1, tz0, tz1, 0, hn, stone, st.floor)
    c.box(x0 + 1, x1 - 1, 1, hn + 1, tz0, tz1, "air")
    c.box(2, w - 2, 1, hn + 1, tz0 + 1, tz1 - 1, "air")
    furnish_worship(c, x0 + 1, x1 - 1, 2, w - 2, 1, "chapel", st, aisle=mid)
    for z in range(tz1 + 1, w - t, 3):                                    # windows and buttresses
        c.box(x0, x0 + 1, 2, hn - 1, z, z + 1, "blue_stained_glass_pane")
        c.box(x1 - 1, x1, 2, hn - 1, z, z + 1, "red_stained_glass_pane")
        c.box(x0 - 1, x0, 1, hn - 1, z + 1, z + 2, stone); c.box(x0 - 2, x0 - 1, 1, hn // 2, z + 1, z + 2, stone)
        c.box(x1, x1 + 1, 1, hn - 1, z + 1, z + 2, stone); c.box(x1 + 1, x1 + 2, 1, hn // 2, z + 1, z + 2, stone)
        c.set(x0 - 2, hn // 2, z + 1, st.accent_wall); c.set(x1 + 1, hn // 2, z + 1, st.accent_wall)   # pinnacles
    for x in (1, w - 2):
        c.box(x, x + 1, 2, hn - 1, (tz0 + tz1) // 2, (tz0 + tz1) // 2 + 1, "yellow_stained_glass_pane")
    ridge = c.gable(x0 - 1, x1 + 1, 0, w, hn, roof, fill=(x0, x1, 1, w, stone), axis="z")
    c.gable(0, w, tz0 - 1, tz1 + 1, hn, roof, fill=(1, w - 1, tz0, tz1, stone), axis="x")
    # Crossing tower: the highest part, with a tall slate spire (a copper dome for the southern set)
    cz = (tz0 + tz1) // 2
    r = 2 if nw >= 7 else 1
    ax0, ax1, az0, az1 = mid - r, mid + r + 1, cz - r, cz + r + 1
    ty = ridge + 2 * r + 6
    c.box(ax0, ax1, ridge - 2, ty + 1, az0, az1, stone)
    for x, z in ((mid, az0), (mid, az1 - 1), (ax0, cz), (ax1 - 1, cz)):
        c.box(x, x + 1, ty - 3, ty - 1, z, z + 1, "glass_pane")            # lancet windows
    if southern:
        c.cylinder(mid, cz, r + 0.5, ty + 1, ty + 3, stone)
        top = c.dome(mid, cz, r + 0.5, ty + 3, "weathered_copper")
        c.set(mid, top + 1, cz, "lightning_rod")
    else:
        c.spire(ax0, ax1, az0, az1, ty + 1, "deepslate_tiles", steep=4)
        for x in (ax0, ax1 - 1):
            for z in (az0, az1 - 1):
                c.box(x, x + 1, ty + 1, ty + 4, z, z + 1, st.accent_wall)  # corner pinnacles
    # Front towers
    th = hn + nw // 2 + 3
    for tx0 in (x0 - t + 1, x1 - 1):
        c.room(tx0, tx0 + t, w - t, w, 0, th, stone)
        c.box(tx0 + 1, tx0 + t - 1, th - 3, th - 1, w - t, w, "air")
        c.box(tx0, tx0 + t, th - 3, th - 1, w - t + 1, w - 1, "air")
        c.box(tx0, tx0 + t, th, th + 1, w - t, w, stone)
        c.crenels(tx0, tx0 + t, w - t, w, th + 1, (st.merlon or stone))
        if southern:
            c.hip(tx0 - 1, tx0 + t + 1, w - t - 1, w + 1, th + 1, roof)
        else:
            c.spire(tx0, tx0 + t, w - t, w, th + 1, "deepslate_tiles", steep=3)
        c.box(tx0 + t // 2, tx0 + t // 2 + 1, th - 10, th - 6, w - 1, w, "glass_pane")   # lancet window
        c.banner(tx0 + t // 2, th - 5, w, col)
    # Facade: rose window and portal
    vertical_disc(c, mid, hn - 2, w - 1, max(1.5, (nw - 3) / 2),
                  ["red_stained_glass", "yellow_stained_glass", "blue_stained_glass"])
    c.box(mid - 1, mid + 2, 1, 5, w - 1, w, "air")
    c.box(mid - 1, mid + 2, 5, 6, w - 1, w, "chiseled_stone_bricks")
    c.box(mid - 1, mid + 2, 3, 5, w - 2, w - 1, "chiseled_stone_bricks")   # arch over the doors
    c.door(mid - 1, 1, w - 2, wood="dark_oak"); c.door(mid + 1, 1, w - 2, wood="dark_oak")
    c.box(mid, mid + 1, 1, 3, w - 2, w - 1, "chiseled_stone_bricks")
    if southern:                                                           # striped marble walls
        band, sid = c.id("polished_deepslate"), c.id(stone)
        for y in range(2, c.a.shape[1] - c.below, 3):
            layer = c.a[:, y + c.below, :]
            layer[layer == sid] = band


def mosque(c, w, st, col, T, ctx):
    """Mosque Wonder: the model of the game for each set (Djenne, Taj Mahal, Samarra)."""
    (djenne if st.torons else taj if st.eaves else samarra)(c, w, st, col, T, ctx)


def samarra(c, w, st, col, T, ctx):
    """Saracen Wonder: the spiral minaret of Samarra in a court with a low arcade (Middle Eastern)."""
    c.box(0, w, 0, 1, 0, w, st.stone2)
    c.walls(0, w, 1, 4, 0, w, st.stone)                                 # arcade around the court
    c.walls(0, w, 4, 5, 0, w, st.accent)
    for k in range(2, w - 2, 3):
        for x, z in ((k, 0), (k, w - 1), (0, k), (w - 1, k)):
            c.box(x, x + 1, 1, 3, z, z + 1, "air")
            c.set(x, 3, z, st.dome)                                       # blue tiles over each arch
    mid = w // 2
    c.box(mid - 1, mid + 2, 1, 4, w - 1, w, "air")                        # entrance
    cx = (w - 1) / 2
    r0, n, th = w * 0.3, 5, max(4, round(w * 0.25))
    c.cylinder(cx, cx, r0 + 1, 1, 2, st.stone2)
    y = 2
    for i in range(n):                                                    # tapering tiers with a ramp ledge
        r = r0 - i * (r0 - 1.8) / (n - 1)
        c.cylinder(cx, cx, r, y, y + th, st.stone)
        c.cylinder(cx, cx, r + 0.7, y, y + 1, st.stone2)
        for k in range(th * 4):                                           # the spiral ramp
            a = 2 * math.pi * (k / (th * 4) + i * 0.25)
            x, z = int(round(cx + (r + 0.4) * math.cos(a))), int(round(cx + (r + 0.4) * math.sin(a)))
            c.set(x, y + k // 4, z, st.stone2)
        y += th
    # A hall in the lowest tier, with a door to the south through the ramp
    hr = int(r0) - 1
    c.cylinder(cx, cx, r0 - 1, 2, 1 + th, "air")
    c.box(mid, mid + 1, 2, 4, mid + hr, w - 1, "air")
    c.door(mid, 2, mid + hr)
    q = (r0 - 1) / math.sqrt(2)                                           # the square inside the round wall
    h0, h1 = math.ceil(cx - q), math.floor(cx + q) + 1
    throne_hall(c, h0, h1, h0, h1, 2, st, col, aisle=mid)
    for x, z in ((mid - 1, mid - 1), (mid + 1, mid - 1), (mid - 1, mid + 1), (mid + 1, mid + 1)):
        c.box(x, x + 1, y, y + 2, z, z + 1, st.accent)                    # kiosk on the top
    top = c.dome(mid, mid, 1.6, y + 2, st.dome)
    c.set(mid, top + 1, mid, "lightning_rod")
    c.banner(mid - 2, 3, w, col); c.banner(mid + 2, 3, w, col)


def taj(c, w, st, col, T, ctx):
    """Wonder of the South Asian set (Taj Mahal): a block with iwan arches, a large white dome and small
    domed kiosks on the corners."""
    c.box(0, w, 0, 1, 0, w, st.stone2)
    c.box(1, w - 1, 1, 2, 1, w - 1, st.stone)                             # plinth
    a, b, h = 3, w - 3, max(7, round(w * 0.4))
    c.room(a, b, a, b, 1, h, st.accent, st.floor)
    c.walls(a, b, h - 1, h, a, b, "blue_terracotta")                      # tile band
    c.box(a, b, h, h + 1, a, b, st.stone)
    mid = w // 2
    for side in "nesw":                                                   # one iwan arch on each side
        for d in range(-2, 3):
            x, z = {"n": (mid + d, a), "s": (mid + d, b - 1), "w": (a, mid + d), "e": (b - 1, mid + d)}[side]
            c.box(x, x + 1, 2, h - 2, z, z + 1, st.dome if abs(d) == 2 else "air")
            c.set(x, h - 2, z, st.dome)
    c.door(mid, 2, b - 2)
    furnish_worship(c, a + 1, b - 1, a + 1, b - 2, 2, "mosque", st, aisle=mid)
    cx = (w - 1) / 2
    rd = (b - a) / 2 - 2
    c.cylinder(cx, cx, rd - 0.5, h + 1, h + 5, st.dome)                   # drum
    top = c.dome(cx, cx, rd + 0.5, h + 5, st.dome)
    top = c.cone(cx, cx, 2, top + 1, st.dome)                              # the onion tip
    c.set(mid, top + 1, mid, "gold_block"); c.set(mid, top + 2, mid, "lightning_rod")
    for x in (a + 1, b - 2):                                               # chhatris on the corners
        for z in (a + 1, b - 2):
            for px, pz in ((x - 1, z - 1), (x + 1, z - 1), (x - 1, z + 1), (x + 1, z + 1)):
                c.box(px, px + 1, h + 1, h + 3, pz, pz + 1, "quartz_pillar")
            c.dome(x, z, 1.6, h + 3, st.dome)
            c.set(x, h + 5, z, "lightning_rod")
    c.banner(mid - 3, h - 2, b, col); c.banner(mid + 3, h - 2, b, col)


def djenne(c, w, st, col, T, ctx):
    """Malian Wonder (Great Mosque of Djenne): a mud-brick hall with buttresses, pinnacles, wooden beams
    (torons) and three towers on the front."""
    c.box(0, w, 0, 1, 0, w, st.stone2)
    a, b, h = 2, w - 2, max(7, round(w * 0.4))
    c.room(a, b, a, b, 0, h, st.stone, st.floor)
    furnish_worship(c, a + 1, b - 1, a + 1, b - 3, 1, "mosque", st, aisle=w // 2)
    c.flat_roof(a, b, a, b, h, st.roof)
    for k in range(a, b, 3):                                               # buttresses with pinnacles
        for x, z in ((k, a - 1), (k, b), (a - 1, k), (b, k)):
            c.box(x, x + 1, 1, h + 2, z, z + 1, st.stone)
            c.set(x, h + 2, z, "mud_brick_wall")
    for y in (3, 6):                                                       # torons
        for k in range(a + 1, b - 1, 3):
            c.set(k, y, a - 1, "stripped_oak_log[axis=z]"); c.set(k, y, b, "stripped_oak_log[axis=z]")
            c.set(a - 1, y, k, "stripped_oak_log[axis=x]"); c.set(b, y, k, "stripped_oak_log[axis=x]")
    mid = w // 2
    for tx in (mid - 6, mid, mid + 5):                                     # three towers on the front
        th = h + (12 if tx == mid else 9)
        c.box(tx - 1, tx + 2, 1, th, b - 3, b, st.stone)
        for x in (tx - 1, tx + 1):
            c.set(x, th, b - 1, "mud_brick_wall")
        c.set(tx, th, b - 1, "mud_brick_wall"); c.set(tx, th + 1, b - 1, "mud_brick_wall")
        for y in range(4, th - 1, 3):
            c.set(tx, y, b, "stripped_oak_log[axis=z]")
    c.box(mid, mid + 1, 1, 4, b - 3, b, "air")                             # entrance in the middle tower
    c.door(mid, 1, b - 3)
    c.banner(mid - 2, 4, b, col); c.banner(mid + 2, 4, b, col)


def pagoda(c, w, st, col, T, ctx):
    """Tall pagoda (Hwangnyongsa, the Korean Wonder): a stone podium with a roof skirt, slim storeys with
    flared eaves and hanging lanterns, and a tall gold finial."""
    c.box(0, w, 0, 2, 0, w, st.stone)
    mid = w // 2
    c.box(mid - 1, mid + 2, 1, 2, w - 1, w, stair("stone_brick_stairs", "north"))
    n = 7 if w >= 20 else 5
    s0 = w / 2 - 3.5
    y = 1
    for i in range(n):
        half = s0 - i * (s0 - 1.5) / max(1, n - 1)
        a = int(round(w / 2 - half))
        b = w - a
        h = 4 if i == 0 else 3
        c.room(a, b, a, b, y, h, st.plaster, st.wood, corner="polished_cinnabar")      # red-painted posts (dancheong)
        c.windows(a, b, a, b, y + h, b="air", step=2)
        if i == 0:
            c.walls(a, b, y + 1, y + 2, a, b, f"{col}_wool")               # player band at the base
            c.box(mid - 1, mid + 2, y + 1, y + 3, b - 1, b, "air")
            c.banner(mid - 2, y + 2, b, col); c.banner(mid + 2, y + 2, b, col)
            throne_hall(c, a + 1, b - 1, a + 1, b - 1, y + 1, st, col, aisle=mid)
        e = 2 if i < 2 else 1                                                 # deep eaves on the lower storeys
        c.hip(a - e, b + e, a - e, b + e, y + h + 1, st.roof, layers=e + 1, flare=True)
        c.box(a + 1, b - 1, y + h + 1 + e, y + h + 2 + e, a + 1, b - 1, f"{family(st.roof)[1]}[type=bottom]")
        for x, z in ((a - e, a - e), (b + e - 1, a - e), (a - e, b + e - 1), (b + e - 1, b + e - 1)):
            c.set(x, y + h, z, "lantern[hanging=true]")
        y += h + 1 + e
    c.box(mid, mid + 1, y - 1, y + 6, mid, mid + 1, "gold_block")            # finial (sangryun)
    c.set(mid, y + 6, mid, "lightning_rod")


def pyramid(c, w, st, col, T, ctx):
    """Stepped pyramid (Mayan and Aztec Wonders): steep terraces with relief panels and a painted band in the
    player color, a wide staircase with balustrades on the south side, and a temple with a roof comb on top."""
    top_w = max(5, w // 3)
    n = (w - top_w) // 2
    k = 3 if w >= 15 else 2                                                # height of one terrace
    for L in range(n):
        y = k * L
        c.box(L, w - L, y, y + k, L, w - L, st.stone)
        c.walls(L, w - L, y + k - 1, y + k, L, w - L, f"{col}_concrete")   # painted band
        if k > 2:                                                          # relief panels
            for i in range(L + 1, w - L - 1, 3):
                for x, z in ((i, L), (i, w - L - 1), (L, i), (w - L - 1, i)):
                    c.set(x, y + 1, z, "chiseled_stone_bricks")
    H = k * n
    mid = w // 2
    for L in range(n):                                                     # steep staircase with balustrades
        z, y = w - 1 - L, k * L
        c.box(mid - 2, mid + 3, y, y + k - 1, z, z + 1, "stone_bricks")
        c.box(mid - 2, mid + 3, y + k - 1, y + k, z, z + 1, stair("stone_brick_stairs", "north"))
        c.box(mid - 2, mid + 3, y + k, H, z, z + 1, "air")
        for x in (mid - 3, mid + 3):
            c.box(x, x + 1, y, y + k + 1, z, z + 1, "polished_granite")
    a, b, y = n, w - n, H
    c.box(a - 1, b + 1, y - 1, y, a - 1, b + 1, "polished_andesite")
    th = 5
    c.room(a, b, a, b - 1, y - 1, th, st.stone)
    c.box(mid - 1, mid + 2, y, y + 3, b - 2, b - 1, "air")                 # temple entrance
    throne_hall(c, a + 1, b - 1, a + 1, b - 2, y, st, col, aisle=mid)
    c.walls(a, b, y + th - 1, y + th, a, b - 1, f"{col}_concrete")
    c.box(a, b, y + th, y + th + 1, a, b - 1, st.stone)
    c.box(a + 1, b - 1, y + th + 1, y + th + 5, mid, mid + 1, "chiseled_stone_bricks")    # roof comb
    for x in (a, b - 1):
        c.set(x, y, b - 1, "campfire")                                     # braziers
    c.banner(mid - 2, y + 2, b - 1, col); c.banner(mid + 2, y + 2, b - 1, col)


def temple(c, w, st, col, T, ctx):
    """Angkor Wat (the Khmer Wonder): three grey stone terraces with a band in the player color and stairs on
    all sides, a gallery on the top terrace, and five lotus-bud towers (prangs) with gold tips."""
    stone, trim, wall = "stone_bricks", "chiseled_stone_bricks", "stone_brick_wall"
    mid = w // 2
    step = max(1, w // 10)                           # inset of each terrace
    for L in range(3):
        a, b = L * step, w - L * step
        c.box(a, b, L * 2, L * 2 + 2, a, b, stone)
        c.walls(a, b, L * 2, L * 2 + 1, a, b, f"{col}_wool")
        c.crenels(a, b, a, b, L * 2 + 2, wall)
        for x in (a, b - 1):                         # pinnacles on the corners
            for z in (a, b - 1):
                c.set(x, L * 2 + 2, z, trim); c.set(x, L * 2 + 3, z, "gold_block")
    top = 6
    for L in range(top):                             # stairs up the middle of each side
        for face, (x0, x1, z0, z1) in {"north": (mid - 1, mid + 2, w - 1 - L, w - L),
                                       "south": (mid - 1, mid + 2, L, L + 1),
                                       "west": (w - 1 - L, w - L, mid - 1, mid + 2),
                                       "east": (L, L + 1, mid - 1, mid + 2)}.items():
            c.box(x0, x1, L, L + 1, z0, z1, stair("stone_brick_stairs", face))
            c.box(x0, x1, L + 1, top + 2, z0, z1, "air")

    def tower(x0, z0, s, body, h):
        c.room(x0, x0 + s, z0, z0 + s, top - 1, body, stone, corner=trim)
        cx, cz = x0 + (s - 1) / 2, z0 + (s - 1) / 2
        for k in range(h):                           # the bud: rings of stone, gold near the tip
            r = max(0.5, (s / 2 + 0.5) * (1 - (k / h) ** 1.5) ** 0.8)
            b = "gold_block" if k >= h - 2 else trim if k % 2 else stone
            c.cylinder(cx, cz, r, top + body + k, top + body + k + 1, b)
        c.box(x0 + s // 2, x0 + s // 2 + 1, top + body + h, top + body + h + 2, z0 + s // 2, z0 + s // 2 + 1,
              "gold_block")
        return top + body + h + 1

    a = 2 * step                                     # the top terrace
    small = max(3, (w - 2 * a) // 4) | 1
    big = max(5, (w - 2 * a) // 2 - 1) | 1
    for x0 in (a, w - a - small):
        for z0 in (a, w - a - small):
            tower(x0, z0, small, 2, max(4, w // 3))
    m0 = mid - big // 2
    tower(m0, m0, big, 3, max(6, w * 3 // 4))
    furnish_worship(c, m0 + 1, m0 + big - 1, m0 + 1, m0 + big - 1, top, "shrine", st, aisle=mid)
    c.door(mid, top, m0 + big - 1)
    c.banner(mid - 1, top + 2, m0 + big, col); c.banner(mid + 1, top + 2, m0 + big, col)


WONDERS = {"cathedral": cathedral, "mosque": mosque, "pagoda": pagoda, "pyramid": pyramid, "temple": temple}


def wonder(c, w, st, col, T, ctx):
    WONDERS.get(st.wonder, cathedral)(c, w, st, col, T, ctx)


def copper_fittings(c, bars=True):
    """Copper lanterns, chains and bars (bars=False: keep iron bars, as on a portcullis) for the rich buildings
    (#543): waxed, so they do not oxidize in the game. A hanging lantern under a high ceiling hangs on a copper chain."""
    for i in np.unique(c.a[c.a >= 0]):
        name, br, props = c.B.states[i].split(":")[-1].partition("[")
        if name in COPPER and (bars or name != "iron_bars"):
            c.a[c.a == i] = c.id(COPPER[name] + br + props)
    hang, empty = c.id(COPPER["lantern"] + "[hanging=true]"), (-1, c.id("air"))
    for x, y, z in zip(*np.nonzero(c.a == hang)):
        top = y + 1
        while top < min(y + 8, c.a.shape[1]) and c.a[x, top, z] in empty:
            top += 1
        if y + 1 < top < c.a.shape[1] and c.a[x, top, z] not in empty:             # a ceiling within reach
            c.a[x, y + 1:top, z] = c.id(COPPER["iron_chain"] + "[axis=y]")


# --------------------------------------------------------------------------------------------
# Selection and placement
# --------------------------------------------------------------------------------------------
FOOTPRINT = [(r["name"], r["size"]) for r in units.rows("footprint.jsonl")]   # the first word in the name wins


def footprint(name):
    for word, size in FOOTPRINT:
        if word in name:
            return size
    return 2


DESIGNS = units.rows("designs.jsonl")   # a part of the name -> the design function and its arguments; the first wins


def select(name):
    """AoE2 building name -> (design function, extra arguments)."""
    for r in DESIGNS:
        if r["name"] in name:
            return globals()[r["design"]], r.get("args", {})
    return generic, {}


def is_wall(name):
    return any(r["name"] in name for r in DESIGNS if r.get("wall"))


SWAP = {"axis=x": "axis=z", "axis=z": "axis=x", "facing=south": "facing=east", "facing=east": "facing=south",
        "facing=north": "facing=west", "facing=west": "facing=north", "shape=north_south": "shape=east_west",
        "shape=east_west": "shape=north_south"}


def transpose(c):
    """Swap x and z of a canvas (for gates along the z axis), with block directions."""
    a = c.a.transpose(2, 1, 0).copy()
    for i in np.unique(a[a >= 0]):
        s = c.B.states[i]
        t = s
        for k, v in SWAP.items():
            if k in s:
                t = t.replace(k, "\0" + v)       # mark to avoid swapping twice
        t = t.replace("\0", "")
        if t != s:
            a[c.a.transpose(2, 1, 0) == i] = c.B(t)
    c.a = a


CLOCKWISE = {"north": "east", "east": "south", "south": "west", "west": "north"}


def turn_state(s, k):
    """Block state s after k clockwise quarter turns (seen from above): facing, axis, rotation, the side
    properties of fences, walls and panes, and rail shapes."""
    if "[" not in s:
        return s
    name, props = s[:-1].split("[", 1)
    keys = [kv.split("=")[0] for kv in props.split(",")]
    d = dict(kv.split("=") for kv in props.split(","))
    for _ in range(k % 4):
        t = {}
        for key, v in d.items():
            if key in ("facing", "axis") or key == "shape" and "_" in v and any(w in v for w in CLOCKWISE):
                if v in ("north_south", "east_west"):
                    v = "east_west" if v == "north_south" else "north_south"
                elif v.startswith("ascending_"):
                    v = "ascending_" + CLOCKWISE[v[10:]]
                elif key == "shape":                                # rail curve: north/south part first
                    a, b = (CLOCKWISE[w] for w in v.split("_"))
                    v = f"{a}_{b}" if a in ("north", "south") else f"{b}_{a}"
                else:
                    v = {"x": "z", "z": "x"}.get(v, CLOCKWISE.get(v, v))
            elif key == "rotation":                                 # signs, banners, skulls: 4 = a quarter
                v = str((int(v) + 4) % 16)
            t[CLOCKWISE.get(key, key)] = v
        d = t
    return f"{name}[" + ",".join(f"{key}={d[key]}" for key in keys + [x for x in d if x not in keys] if key in d) + "]"


def turn(c, k):
    """Turn a square canvas by k clockwise quarter turns (seen from above), with block directions."""
    a = np.rot90(c.a, k, axes=(0, 2)).copy()
    out = a.copy()
    for i in np.unique(a[a >= 0]):
        t = turn_state(c.B.states[i], k)
        if t != c.B.states[i]:
            out[a == i] = c.B(t)
    c.a = out


SOFT_BARRIER = -3    # canvas marker: barrier that only fills free space
BARRIERS = True      # fill the free space of footprints with barrier blocks (option --no-barriers)
TURN = 0             # clockwise quarter turns of the map (option --orientation); buildings turn with it


def place_building(E, cols, B, o, players, walls, gates):
    name, T = o["name"], cols.T
    info = players.get(o["player"], {"arch": "western", "color": "light_gray"})
    st, col = ARCH[info["arch"]], info["color"]
    fn, kw = select(name)
    ux, uy = o["x"], o["y"]
    size = footprint(name)

    if fn is farm:
        # Like the game: rows of crops with furrows of bare soil between them, along tile y (they turn with
        # --orientation), and a path around the plot. Some rows are not ripe yet.
        x0, z0 = int(round((ux - 1.5) * T)), int(round((uy - 1.5) * T))
        o["footprint"] = [x0, z0, x0 + 3 * T, z0 + 3 * T]                   # for aoe2mc.json
        rng = np.random.default_rng(abs((x0 * 73856093) ^ (z0 * 19349663)) % (2 ** 32))
        for x in range(max(0, x0), min(cols.n, x0 + 3 * T)):
            for z in range(max(0, z0), min(cols.n, z0 + 3 * T)):
                if cols.wtop[x, z] == cols.top[x, z]:
                    y = int(cols.top[x, z])
                    edge = x in (x0, x0 + 3 * T - 1) or z in (z0, z0 + 3 * T - 1)
                    row = (x - x0 if TURN % 2 == 0 else z - z0) % 2 == 1
                    age = rng.choice((7, 6, 5), p=(.7, .2, .1))
                    E.add([x, x], [y, y + 1], [z, z],
                          [B("farmland[moisture=7]") if not edge else B("dirt_path"),
                           B(f"wheat[age={age}]") if row and not edge else 0])
        return

    along_z = False
    if fn is bridge:
        letter = name.split("BRIDGE_")[1][:1]
        along_z = (letter in ("B", "D")) != (TURN % 2 == 1)
        w, L = 3 * T, 2 * T
        if along_z:
            x0, z0 = int(round((ux - 1.5) * T)), int(round((uy - 1) * T))
            fx, fz = w, L
        else:
            x0, z0 = int(round((ux - 1) * T)), int(round((uy - 1.5) * T))
            fx, fz = L, w
    elif fn is aqueduct:
        along_z = gates.get(id(o), False)
        w = T
        x0, z0 = int(round((ux - 0.5) * T)), int(round((uy - 0.5) * T))
        fx, fz = w, w
    elif fn is gate and str(gates.get(id(o))).startswith("diag"):
        w = fx = fz = 3 * T
        x0, z0 = int(round((ux - 1.5) * T)), int(round((uy - 1.5) * T))
    elif fn is gate:
        along_z = gates.get(id(o), False)
        w = 4 * T
        if along_z:
            x0, z0 = int(round((ux - 0.5) * T)), int(round((uy - 2) * T))
            fx, fz = T, w
        else:
            x0, z0 = int(round((ux - 2) * T)), int(round((uy - 0.5) * T))
            fx, fz = w, T
    else:
        w = size * T
        x0, z0 = int(round((ux - size / 2) * T)), int(round((uy - size / 2) * T))
        fx, fz = w, w

    xs = range(max(0, x0), min(cols.n, x0 + fx))
    zs = range(max(0, z0), min(cols.n, z0 + fz))
    if not len(xs) or not len(zs):
        return
    o["footprint"] = [x0, z0, x0 + fx, z0 + fz]                         # for aoe2mc.json
    area = cols.wtop[xs.start:xs.stop, zs.start:zs.stop]
    base = int(area.max())
    if fn not in (gate, bridge, wooden_bridge):                      # units on a bridge stand on its deck
        cols.blocked[xs.start:xs.stop, zs.start:zs.stop] = True
    is_dock = fn in (dock, harbor, bridge, wooden_bridge, fish_trap, shipyard, port, mole, harbor_chain, flagship)
    wet = area > cols.top[xs.start:xs.stop, zs.start:zs.stop]
    water_y = int(area[wet].max()) if wet.any() else cols.water_y       # the surface of this water body (#165)
    if fn is bridge:                                                     # one deck height for all pieces (#192)
        base = bridge_deck(cols, x0 + fx // 2, z0 + fz // 2, along_z, water_y) - 1
    opening = None                                                       # the passage of a gate stays open
    if fn is gate and not str(gates.get(id(o))).startswith("diag"):
        opening = (range(z0 + T, z0 + fz - T), None) if along_z else (None, range(x0 + T, x0 + fx - T))
    E.footprint = (x0, x0 + fx, z0, z0 + fz)
    if not is_dock:                                                      # foundation under the floor
        found = st.stone2
        for x in xs:
            for z in zs:
                top, wtop = int(cols.top[x, z]), int(cols.wtop[x, z])
                if wtop > top and opening and (z in opening[0] if along_z else x in opening[1]):
                    continue                                             # water flows through the gate
                # on water: a footing from the bed, not a block that floats on the surface
                E.box(x, x + 1, (top if wtop > top else wtop) + 1, base + 1, z, z + 1, found)

    ctx = {"name": name, "deck": max(1, water_y + 2 - base), "water": water_y - base, "diag": gates.get(id(o)) in ("diag+", "diag-"),
           "origin": (int(ux) * T if not along_z else int(uy) * T, 0)}
    if fn in (bridge, wooden_bridge):
        BRIDGE_CELLS.update((x, z) for x in xs for z in zs)
    if fn is wooden_bridge:
        tx, ty = int(ux), int(uy)
        rails = []
        for side, (dx, dy) in (("n", (0, -1)), ("s", (0, 1)), ("w", (-1, 0)), ("e", (1, 0))):
            nx, ny = tx + dx, ty + dy
            if (nx, ny) in WOOD_BRIDGE_TILES:
                continue
            bx, bz = nx * T + T // 2, ny * T + T // 2
            if cols.inside(bx, bz) and cols.wtop[bx, bz] > cols.top[bx, bz]:
                rails.append(side)
        ctx["rails"] = rails
        ns = sum((tx, ty + d) in WOOD_BRIDGE_TILES for d in (-1, 1))
        ew = sum((tx + d, ty) in WOOD_BRIDGE_TILES for d in (-1, 1))
        ctx["along_z"] = ns > ew or (ns == ew and ("w" in rails or "e" in rails))
    if fn is wall_segment:
        tx, ty = int(ux), int(uy)
        ctx["neighbours"] = ((tx, ty - 1) in walls, (tx, ty + 1) in walls, (tx - 1, ty) in walls, (tx + 1, ty) in walls)
        ctx["origin"] = (x0, z0)
    c = Canvas(B, w, height=8 * w + 40, margin=3, below=12 if is_dock else 0)
    c.rng = np.random.default_rng(abs((x0 * 73856093) ^ (z0 * 19349663)) % (2 ** 32))
    if fn not in MONUMENTAL:
        st = vary(st, c.rng)
    wood = st.wood.replace("_planks", "")
    c.trapdoor = f"{wood}_trapdoor" if wood in WOODS else "spruce_trapdoor"
    fn(c, w, st, col, T, ctx, **kw)
    weather(c)
    if fn not in NO_PROPS:
        decorate(c, fx, fz)
    if fn in (castle, wonder):                                           # the rich buildings (#543)
        copper_fittings(c, bars=fn is wonder)
    if TURN and fn not in (gate, aqueduct, bridge, wooden_bridge, wall_segment):    # these follow their neighbours
        turn(c, TURN)
    if along_z:
        transpose(c)
    if gates.get(id(o)) == "diag-":
        c.a = c.a[:, :, ::-1].copy()                                     # mirror: the other diagonal
    if o.get("ref") is not None and fn not in (gate, bridge, wooden_bridge, fish_trap, scaffold_walk, aqueduct):
        up = getattr(c, "upper", 0)                                      # the floor of an upper hall
        up = up if up and rooms(c, fx, fz, up) else 0                    # a small hall (--tile-size 1, 2): no room
        INSIDE[o["ref"]] = ([(x0 + x, z0 + z) for x, z in rooms(c, fx, fz, up) if cols.inside(x0 + x, z0 + z)],
                            base + 1 + up, (x0 + fx // 2, z0 + fz // 2))
    if BARRIERS and fn not in (gate, bridge, wooden_bridge, fish_trap, scaffold_walk):
        barriers(c, fx, fz, under=fn is town_center)
    if fn in (gate, town_center):           # only the passage is free: units on the towers move out (#577, #865)
        head = c.a[c.m:c.m + fx, c.below + 1:c.below + 3, c.m:c.m + fz]
        solid = ((head >= 0) & (head != B("air"))).any(1)
        cols.blocked[xs.start:xs.stop, zs.start:zs.stop] = solid[xs.start - x0:xs.stop - x0, zs.start - z0:zs.stop - z0]
        o["open"] = [[x, z] for x in xs for z in zs if not solid[x - x0, z - z0]]     # for aoe2mc.json and the replay
        for x in xs:                        # on a slope the foundation lifts the floor: units stand on it (#773)
            for z in zs:
                if not solid[x - x0, z - z0]:
                    FLOORS[(x, z)] = base + 1
    ix, iy, iz = np.nonzero(c.a >= 0)
    # Outside the footprint only parts above head height (roof edges, tower tops, sails) are kept;
    # Edits checks this against the real ground of each column.
    E.footprint = (x0, x0 + fx, z0, z0 + fz)
    if len(ix):
        ids = c.a[ix, iy, iz].astype(np.uint16)
        E.add(x0 - c.m + ix, base - c.below + iy, z0 - c.m + iz, ids)
        if c.goods:                                                      # 3 items per shelf, in turn from the goods
            k = np.flatnonzero(np.isin(ids, [i for i in np.unique(ids).tolist() if "_shelf[" in B.states[i]]))
            for n, j in enumerate(k.tolist()):
                SHELVES[(int(x0 - c.m + ix[j]), int(base - c.below + iy[j]), int(z0 - c.m + iz[j]))] = \
                    tuple(c.goods[(3 * n + i) % len(c.goods)] for i in range(3))
    sx, sy, sz = np.nonzero(c.a == SOFT_BARRIER)
    if len(sx):
        E.add(x0 - c.m + sx, base - c.below + sy, z0 - c.m + sz, B("barrier"), hard=False)
    E.footprint = None


def bridge_deck(cols, x, z, along_z, water_y):
    """The deck height of the bridge through block (x, z). Find the nearest water on the line along the bridge axis,
    go to its two banks, and take the land one tile behind each bank (behind the shore slope); the deck is at the
    lower of the two, but 2 above the water at least. All pieces of a bridge get the same height."""
    dx, dz = (0, 1) if along_z else (1, 0)
    wet = lambda i: cols.inside(x + i * dx, z + i * dz) and cols.wtop[x + i * dx, z + i * dz] > cols.top[x + i * dx, z + i * dz]
    near = next((i for d in range(4 * cols.T) for i in (d, -d) if wet(i)), None)
    if near is None:
        return water_y + 2
    banks = []
    for sgn in (-1, 1):
        i = near
        while wet(i):
            i += sgn
        i = i + sgn * cols.T if cols.inside(x + (i + sgn * cols.T) * dx, z + (i + sgn * cols.T) * dz) else i
        if cols.inside(x + i * dx, z + i * dz):
            banks.append(int(cols.top[x + i * dx, z + i * dz]))
    return max(water_y + 2, min(banks) if banks else 0)


WOOD_BRIDGE_TILES = set()
SHELVES = {}             # (x, y, z) of a shelf block -> its 3 item names (#526)
BRIDGE_CELLS = set()     # block columns with a bridge deck (units there stand on the deck)
FLOORS = {}              # (x, z) of a gate passage -> the y where units stand on its floor (#773)
INSIDE = {}              # reference ID of a building -> (free cells of its rooms, their y, center): garrisons (#807)


def plan_walls(objects):
    """Tiles with walls, and the direction of each gate (True = along z, "diag+" / "diag-" = diagonal)."""
    WOOD_BRIDGE_TILES.clear()
    BRIDGE_CELLS.clear()
    FLOORS.clear()
    INSIDE.clear()
    WOOD_BRIDGE_TILES.update((int(o["x"]), int(o["y"])) for o in objects if "WOODEN_BRIDGE" in o["name"])
    walls = set()
    for o in objects:
        if o["kind"] == "B" and is_wall(o["name"]) and "GATE" not in o["name"]:
            walls.add((int(o["x"]), int(o["y"])))
    gates = {}
    aq = {(int(o["x"]), int(o["y"])) for o in objects if o["kind"] == "B" and o["name"] == "AQUEDUCT"}
    for o in objects:
        if o["kind"] == "B" and o["name"] == "AQUEDUCT":
            tx, ty = int(o["x"]), int(o["y"])
            gates[id(o)] = ((tx, ty - 1) in aq or (tx, ty + 1) in aq) and not ((tx - 1, ty) in aq or (tx + 1, ty) in aq)
    for o in objects:
        if o["kind"] == "B" and "GATE" in o["name"]:
            ux, uy = o["x"], o["y"]
            tx, ty = int(ux), int(uy)
            if "WEST_TO_EAST" in o["name"] or "NORTH_TO_SOUTH" in o["name"]:
                # Diagonal gate (3 tiles). Screen west-east is tile (+1, +1), screen north-south is (+1, -1)
                # (#23); the wall tiles next to the gate decide first.
                up = any((tx + d, ty + d) in walls for d in (-2, 2))
                down = any((tx + d, ty - d) in walls for d in (-2, 2))
                ns = ("NORTH_TO_SOUTH" in o["name"]) != (TURN % 2 == 1)        # an odd turn swaps the diagonals
                s = -1 if down and not up or not up and ns else 1
                gates[id(o)] = "diag+" if s > 0 else "diag-"
                walls.update((tx + d, ty + s * d) for d in (-1, 0, 1))
                continue
            on_x = any((int(ux + d), ty) in walls for d in (-2.5, -3, 2, 2.5))
            on_z = any((tx, int(uy + d)) in walls for d in (-2.5, -3, 2, 2.5))
            if (ux % 1 == 0.5) != (uy % 1 == 0.5):
                # the center of a 4 x 1 gate gives its axis; a wall line beside it does not (#3091)
                on_z, on_x = ux % 1 == 0.5, ux % 1 != 0.5
            gates[id(o)] = on_z and not on_x
            for d in range(-2, 2):
                walls.add((tx, int(uy) + d) if gates[id(o)] else (int(ux) + d, ty))
    return walls, gates


# --------------------------------------------------------------------------------------------
# Special and decorative buildings (bridges, aqueducts, tents, landmarks)
# --------------------------------------------------------------------------------------------
def bridge(c, w, st, col, T, ctx):
    """One stone bridge piece along the x axis: 2 tiles long, 3 tiles wide (w = 3 tiles). Like the game (#455):
    piers with cutwaters every tile, vaulted arches between them, a balustrade with posts over the piers."""
    L, deck = 2 * T, ctx["deck"]
    wl = ctx.get("water", deck - 2)                                     # the top water block (local y)
    z0, z1 = 2, w - 2
    sp = T if T >= 3 else L                                             # pier spacing: same at the joins of pieces
    piers = range(0, L, sp)
    c.box(0, L, deck, deck + 1, z0, z1, "stone_bricks")
    c.box(0, L, max(1, wl + 1), deck, z0, z1, "air")
    for p in piers:
        c.box(p, p + 1, -12, deck, z0, z1, "stone_bricks")              # pier down to the bed
        for z in (z0 - 1, z1):                                          # cutwater on each side, up to the deck
            c.box(p, p + 1, -12, deck + 1, z, z + 1, "stone_bricks")
            c.set(p, deck + 1, z, "stone_brick_slab[type=bottom]")
        if deck - 1 > wl and sp > 2:                                    # vault: the arch springs from the pier
            c.box(p + 1, p + 2, deck - 1, deck, z0, z1, "stone_brick_stairs[facing=west,half=top]")
            c.box(p + sp - 1, p + sp, deck - 1, deck, z0, z1, "stone_brick_stairs[facing=east,half=top]")
    for z in (z0, z1 - 1):                                              # balustrade, a post over each pier
        c.box(0, L, deck + 1, deck + 2, z, z + 1, "stone_brick_wall")
        for p in piers:
            c.set(p, deck + 1, z, "chiseled_stone_bricks")
    name = ctx["name"]
    if "CRACKED" in name:                                               # cracked: split stones, a gap in the rail
        c.box(L // 2 - 1, L // 2 + 1, deck, deck + 1, z0, z1, "cracked_stone_bricks")
        c.box(L // 2, L // 2 + 2, deck + 1, deck + 2, z1 - 1, z1, "air")
    if "BROKEN" in name:                                                # broken: the deck stops halfway
        c.box(L // 2, L, deck, deck + 2, z0 - 1, z1 + 1, "air")
        c.box(L // 2, L // 2 + 1, deck, deck + 1, z0, z1, "cracked_stone_bricks")
        c.set(L // 2, deck, z0 + 1, "air"); c.set(L // 2, deck, z1 - 3, "air")


def aqueduct(c, w, st, col, T, ctx):
    """One aqueduct tile: piers and arches carrying a water channel (drawn along x)."""
    h = max(8, 3 * T)
    gx = ctx["origin"][0] // w
    c.box(0, w, h - 2, h, 0, w, "stone_bricks")
    c.box(0, w, h, h + 1, 0, w, "stone_brick_slab[type=bottom]")
    c.box(0, w, h - 1, h, 1, w - 1, "air")                              # channel
    c.box(0, w, h - 2, h - 1, 1, w - 1, "blue_concrete")                 # (dry) water channel floor
    if gx % 2 == 0:
        c.box(0, w, 1, h - 2, 0, w, "stone_bricks")                      # pier
        c.box(0, w, h // 2, h // 2 + 1, 0, w, "chiseled_stone_bricks")
    else:
        c.box(0, 1, h - 4, h - 2, 0, w, "stone_bricks")                  # arch
        c.box(w - 1, w, h - 4, h - 2, 0, w, "stone_bricks")
        c.box(0, w, h - 3, h - 2, 0, w, "stone_bricks")


def army_tent(c, w, st, col, T, ctx):
    """Tents (#454), like the game models: ARMY_TENT_A, C, E are round with upright canvas walls, player color trim and
    a low dome (the large army tent), B, D, F are square pavilions with wooden poles and a pyramid roof (the small one).
    GREEK_ARMY_TENT is a ridge tent of canvas, TENT_A to E are nomad tents of brown hide with a peak. The door is
    in the south."""
    name = ctx.get("name", "ARMY_TENT_A")
    if "GREEK" in name:
        return ridge_tent(c, w, col)
    if name.startswith("TENT"):
        return hide_tent(c, w, col, name)
    m, cx = w // 2, (w - 1) / 2
    if w < 4:
        c.box(0, w, 1, 2, 0, w, "white_wool")
        c.flag(m, 2, m, col, 1)
        return
    if name[-1:] in "BDF":                                 # the small army tent: a square pavilion
        a, b = 1, w - 1
        c.walls(a, b, 1, 5, a, b, "white_wool")
        for x in (a, b - 1):
            for z in (a, b - 1):
                c.box(x, x + 1, 1, 6, z, z + 1, "stripped_spruce_log[axis=y]")   # poles up to the roof edge
        k = 1
        while b - a > 1:                                   # canvas roof, steps of wool
            c.walls(a, b, 4 + k, 5 + k, a, b, "white_wool")
            a, b, k = a + 1, b - 1, k + 1
        c.box(a, b, 4 + k, 5 + k, a, b, "white_wool")
        c.box(m - 1, m + 1, 1, 4, w - 2, w - 1, "air")       # open front with flaps in the player color
        c.box(m - 2, m - 1, 1, 4, w - 2, w - 1, f"{col}_wool"); c.box(m + 1, m + 2, 1, 4, w - 2, w - 1, f"{col}_wool")
        c.box(2, w - 2, 1, 2, 2, w - 2, "yellow_carpet")    # the yellow lining inside
        c.set(0, 1, w - 1, "barrel[facing=up,open=false]")
        c.flag(m, 5 + k, m, col, 1)
    else:                                                  # the large army tent: round, upright walls, low dome
        r = w / 2 - 0.3
        c.cylinder(cx, cx, r, 1, 4, "white_wool", hollow=True)
        c.cylinder(cx, cx, r, 1, 2, f"{col}_wool", hollow=True)       # trim at the ground and under the roof
        c.cylinder(cx, cx, r, 4, 5, f"{col}_wool", hollow=True)
        c.cylinder(cx, cx, r - 1, 4, 5, "white_wool")
        c.cylinder(cx, cx, r - 2, 5, 6, "white_wool")
        c.box(m - 1, m + 1, 1, 3, int(cx + r) - 1, w, "air")           # the open door flap
        c.flag(m, 6, m, col, 2)                                       # the center pole
    if w >= 6:                                             # inside (#335): bedrolls along the sides, spears, a lamp
        for x, z in ((2, 2), (w - 3, 2)):
            c.furniture([(x, 1, z, f"{col}_bed[facing=north,occupied=false,part=head]"),
                         (x, 1, z + 1, f"{col}_bed[facing=north,occupied=false,part=foot]")])
        c.furniture([(m, 1, 2, "lightning_rod[facing=up,powered=false,waterlogged=false]"),
                     (m - 1, 1, 2, "lantern[hanging=false,waterlogged=false]")])


def ridge_tent(c, w, col):
    """Greek army tent: a canvas ridge tent (the ridge runs north to south), the door in the south gable, and the
    shield and pots of the player in front."""
    m = w // 2
    z1 = max(w - 1, 2)                                     # the front row stays free for the shield and the pots
    for i in range((w + 1) // 2):                         # cloth slopes of wool stairs, a wool slab on the ridge (#525)
        y = 1 + i
        for x, f in ((i, "east"), (w - 1 - i, "west")):
            c.box(x, x + 1, y, y + 1, 0, z1, "white_wool_slab[type=bottom]" if 2 * i == w - 1 else stair("white_wool_stairs", f))
        c.box(i + 1, w - 1 - i, 1, y + 1, 1, z1 - 1, "air")
    c.box(1, w - 1, 1, (w + 1) // 2, 0, 1, "white_wool")    # the back gable
    for i in range((w + 1) // 2 - 1):
        c.box(i + 1, w - 1 - i, 1 + i, 2 + i, z1 - 1, z1, "light_gray_wool")   # the front gable
    c.box(m - 1, m + 1, 1, 3, z1 - 1, z1, "air")
    if w >= 6:
        c.set(1, 1, w - 1, "decorated_pot[cracked=false,facing=south,waterlogged=false]")
        c.set(w - 2, 1, w - 1, "lightning_rod[facing=up,powered=false,waterlogged=false]")   # a spear
        c.set(m - 2, 2, z1, f"{col}_wall_banner[facing=south]")        # the round shield in the player color
        for x in (2, w - 3):
            c.furniture([(x, 1, 2, f"{col}_bed[facing=north,occupied=false,part=head]"),
                         (x, 1, 3, f"{col}_bed[facing=north,occupied=false,part=foot]")])
        c.furniture([(m, 1, 1, "lantern[hanging=false,waterlogged=false]")])


def cloth_slopes(c, wool, y0, cx, cz):
    """Turn the open steps (nothing above, nothing outside) of a round wool roof from y0 up into wool stairs that rise
    to the centre, so the cloth slopes smoothly (#525)."""
    full, empty = c.id(wool), (-1, c.id("air"))
    n = c.a.shape[0] - c.m - 1                             # keep x + ox inside the canvas (no negative index)
    for x in range(1 - c.m, n):
        for z in range(1 - c.m, n):
            dx, dz = cx - x, cz - z
            if max(abs(dx), abs(dz)) < 0.5:
                continue
            f, ox, oz = (("east", -1, 0) if dx > 0 else ("west", 1, 0)) if abs(dx) >= abs(dz) else \
                (("south", 0, -1) if dz > 0 else ("north", 0, 1))
            for y in range(y0, c.a.shape[1] - c.below - 1):
                if c.get(x, y, z) == full and c.get(x, y + 1, z) in empty and c.get(x + ox, y, z + oz) in empty:
                    c.set(x, y, z, stair(f"{wool}_stairs", f))


def hide_tent(c, w, col, name):
    """Nomad tent: a dome of brown hide with a band of ornaments and a peak, a wide door in the south, rugs, cushions
    and pots in front. The letter changes the height of the peak."""
    m, cx = w // 2, (w - 1) / 2
    r = w / 2 - 0.3
    c.cylinder(cx, cx, r, 1, 3, "brown_wool", hollow=True)
    ring, _, _ = c.disc_mask(cx, cx, r)
    top = c.cone(cx, cx, r - 0.5, 3, "brown_wool")
    for x in range(w):                                     # the ornament band: light stitches on the hide
        for z in range(w):
            if (x + z) % 2 and c.get(x, 2, z) == c.id("brown_wool"):
                c.set(x, 2, z, "white_wool" if (x * 3 + z) % 4 < 2 else "orange_wool")
    peak = 1 + (ord(name[-1]) - ord("A")) % 2
    c.box(m, m + 1, top + 1, top + 1 + peak, m, m + 1, "brown_wool")
    c.set(m, top + 1 + peak, m, "spruce_fence")
    cloth_slopes(c, "brown_wool", 3, cx, cx)
    c.box(m - 1, m + 2, 1, 3, int(cx + r) - 1, w, "air")             # the wide door
    if w >= 6:
        c.box(2, w - 2, 1, 2, 2, w - 3, "red_carpet")
        c.furniture([(2, 1, 2, "blue_wool"), (w - 3, 1, 2, "orange_wool"),       # cushions at the back
                     (m, 1, 2, "lantern[hanging=false,waterlogged=false]")])
        c.set(0, 1, w - 1, "decorated_pot[cracked=false,facing=south,waterlogged=false]")
        c.set(w - 1, 1, w - 1, "barrel[facing=up,open=false]")


def command_tent(c, w, st, col, T, ctx, dropsite=False):
    """Greek commander tent, Macedonian command post: a square canvas tent on a low stone platform."""
    c.box(0, w, 0, 1, 0, w, st.stone2)
    a, b = 1, w - 1
    c.walls(a, b, 1, 3, a, b, "white_wool")
    for x in (a, b - 1):                                   # tent poles at the corners
        for z in (a, b - 1):
            c.box(x, x + 1, 1, 3, z, z + 1, "spruce_fence")
    c.walls(a - 1, b + 1, 3, 4, a - 1, b + 1, f"{col}_wool")   # colored valance under the eaves
    k = 0
    while b - a > 1:                                      # canvas roof, steps of wool
        c.walls(a, b, 4 + k, 5 + k, a, b, "white_wool")
        a, b, k = a + 1, b - 1, k + 1
    c.box(a, b, 4 + k, 5 + k, a, b, "white_wool")
    c.box(w // 2 - 1, w // 2 + 1, 1, 3, w - 2, w - 1, "air")   # open front
    c.set(w // 2 - 1, 1, w - 3, "loom[facing=south]" if not dropsite else "chest[facing=south]")
    if dropsite:
        c.set(w // 2, 1, w - 3, "barrel[facing=up]")
    if w >= 6:                                             # inside (#335): the map table of the commander, a chest, light
        c.set(w // 2 - 1, 1, 2, "cartography_table"); c.set(w // 2, 1, 2, "chest[facing=south,type=single,waterlogged=false]")
        c.set(2, 1, 2, "lantern[hanging=false,waterlogged=false]"); c.set(w - 3, 1, 2, f"{col}_banner[rotation=0]")
        c.box(2, w - 2, 1, 2, 3, w - 3, f"{col}_carpet")
        c.box(w // 2 - 1, w // 2 + 1, 1, 2, w - 4, w - 2, "air")    # the way from the door stays free
        c.set(w // 2 - 1, 1, w - 3, "loom[facing=south]" if not dropsite else "chest[facing=south]")
    c.flag(w // 2, 5 + k, w // 2, col, 2)


def storage(c, w, st, col, T, ctx):
    """An open storehouse: a roof on posts over barrels, chests and sacks."""
    m = inset(w)
    c.box(m, w - m, 0, 1, m, w - m, st.floor)
    for x in (m, w - m - 1):
        for z in (m, w - m - 1):
            c.box(x, x + 1, 1, 4, z, z + 1, st.timber)
    c.walls(m + 1, w - m - 1, 1, 3, m, m + 1, st.wood)       # closed back wall
    goods = ["barrel[facing=up]", "chest[facing=south]", "hay_block", "barrel[facing=up]", "composter"]
    for i, x in enumerate(range(m + 1, w - m - 1)):
        c.set(x, 1, m + 1, goods[i % len(goods)])
        if i % 2 == 0:
            c.set(x, 2, m + 1, "barrel[facing=up]")
    top = c.roof(m - 1, w - m + 1, m - 1, w - m + 1, 4, st)
    c.flag(w // 2, top + 1, w // 2, col, 2)


def pasture(c, w, st, col, T, ctx):
    """Like the game (#518): no fence, but a field of trodden grass with low stakes, tall posts at the corners and a
    small felt yurt in the middle (white felt, bands in the player color, a wooden crown), with hay and a trough."""
    rng = c.rng
    cx = (w - 1) / 2
    for x in range(w):                                     # trodden ground, more dirt near the yurt
        for z in range(w):
            d = math.hypot(x - cx, z - cx) / (w / 2)
            if d < 1 and rng.random() < 0.7 - 0.4 * d:
                c.set(x, 0, z, "coarse_dirt" if rng.random() < 0.6 else "rooted_dirt")
    for k in range(12):                                    # low stakes on a ring
        a = 2 * math.pi * (k + rng.random() * 0.4) / 12
        x, z = int(round(cx + (w / 2 - 1.5) * math.cos(a))), int(round(cx + (w / 2 - 1.5) * math.sin(a)))
        c.set(x, 1, z, "spruce_fence")
    for x in (0, w - 1):                                   # tall posts at the corners
        for z in (0, w - 1):
            c.box(x, x + 1, 1, 3, z, z + 1, "spruce_fence")
            c.set(x, 3, z, "white_wool")
    r = max(1.5, w / 5)
    c.cylinder(cx, cx, r, 1, 3, "white_wool", hollow=True)
    ring, X, Z = c.disc_mask(cx, cx, r)
    c._fill_mask(ring & ~c.disc_mask(cx, cx, r - 1)[0], 1, 2, f"{col}_wool")     # the lower band
    c.cylinder(cx, cx, r + 0.3, 3, 4, "white_wool")
    rim = c.disc_mask(cx, cx, r + 0.3)[0] & ~c.disc_mask(cx, cx, r - 0.7)[0] & ((X + Z) % 2 == 1)
    c._fill_mask(rim, 3, 4, f"{col}_wool")                 # a zig-zag at the edge of the roof
    c.cylinder(cx, cx, r - 0.9, 4, 5, "white_wool")
    c.set(w // 2, 5 if r < 2 else 4, w // 2, "spruce_trapdoor[facing=north,half=bottom,open=false]")    # the crown
    zd = int(cx + r)
    c.door(w // 2, 1, zd, "south", "spruce")
    xe = int(cx + r) + 1                                   # a hay rack and a trough at the east side
    if xe < w - 1:
        c.set(xe, 1, w // 2 - 1, "hay_block"); c.set(xe, 1, w // 2, "hay_block")
        c.set(xe, 1, w // 2 + 1, "water_cauldron[level=3]")


def settlement(c, w, st, col, T, ctx):
    """A goods stall under a thatched roof, with logs, stones and baskets of food next to it."""
    a, b = 2, w - 2
    for x in (a, b - 1):
        for z in (a, b - 1):
            c.box(x, x + 1, 1, 4, z, z + 1, "stripped_spruce_log")
    for y in (1, 2):                                       # shelves with food
        c.box(a + 1, b - 1, y, y + 1, a, a + 1, "spruce_slab[type=top]" if y == 2 else "barrel[facing=up]")
    c.box(a + 1, b - 1, 3, 4, a, a + 1, "spruce_slab[type=bottom]")
    c.set(a + 1, 1, a + 1, "melon"); c.set(b - 2, 1, a + 1, "pumpkin")
    for k in range(3):                                     # thatch
        c.box(a - 1 + k, b + 1 - k, 4 + k, 5 + k, a - 1 + k, b + 1 - k, "hay_block")
    c.box(0, 1, 1, 3, 1, 3, "oak_log[axis=y]"); c.set(w - 1, 1, 2, "cobblestone"); c.set(w - 1, 1, 3, "mossy_cobblestone")
    c.flag(w - 1, 1, w - 1, col, 2)


def wooden_fort(c, w, st, col, T, ctx):
    """A log tower with a shingle roof inside a palisade of sharp stakes."""
    c.box(0, w, 0, 1, 0, w, "coarse_dirt")
    for x in range(w):                                     # palisade, stakes of two heights
        for z in range(w):
            if x in (0, w - 1) or z in (0, w - 1):
                c.box(x, x + 1, 1, 3 + (x + z) % 2, z, z + 1, "spruce_log[axis=y]")
    c.box(w // 2 - 1, w // 2 + 1, 1, 3, w - 1, w, "air")       # gate
    a, b = 2, w - 2
    c.room(a, b, a, b, 0, 5, "spruce_log[axis=y]", floor=st.floor)
    c.box(a - 1, b + 1, 5, 6, a - 1, b + 1, "spruce_planks")    # gallery
    c.walls(a - 1, b + 1, 6, 7, a - 1, b + 1, "spruce_fence")
    c.door(w // 2, 1, b - 1)
    c.windows(a, b, a, b, 3, b="spruce_fence", step=2)
    top = c.hip(a - 1, b + 1, a - 1, b + 1, 8, "spruce")
    for x in (a, b - 1):
        for z in (a, b - 1):
            c.box(x, x + 1, 6, 8, z, z + 1, "spruce_fence")
    c.flag(w // 2, top + 1, w // 2, col, 2)
    if b - a >= 4:                                         # inside (#441): a ladder to the gallery, stores, a camp
        c.box(a + 1, a + 2, 1, 6, a + 1, a + 2, "ladder[facing=south,waterlogged=false]")
        c.furniture([(b - 2, 1, a + 1, "chest[facing=west,type=single,waterlogged=false]")])
        for x, z, s in ((1, 1, "campfire[facing=south,lit=true,signal_fire=false,waterlogged=false]"),
                        (w - 2, 1, "barrel[facing=up,open=false]"), (w - 2, 2, "barrel[facing=up,open=false]"),
                        (1, w - 3, "grindstone[face=floor,facing=east]"), (1, w - 2, "hay_block[axis=y]")):
            c.set(x, 1, z, s)                              # the yard between the palisade and the tower
        c.set(b - 2, 4, b - 2, "lantern[hanging=true,waterlogged=false]")


def sapper_tunnel(c, w, st, col, T, ctx):
    """A timber-framed tunnel mouth in a mound of earth, with sharp stakes around it."""
    for k in range(3):
        c.box(k, w - k, 1 + k, 2 + k, k, w - 1 - k, ["coarse_dirt", "dirt", "rooted_dirt"][k])
    c.box(w // 2 - 1, w // 2 + 1, 1, 3, 2, w - 1, "air")       # the tunnel
    c.box(w // 2 - 1, w // 2 + 1, 0, 1, 2, w - 1, "dirt_path")
    c.box(w // 2 - 2, w // 2 - 1, 1, 3, w - 3, w - 2, "stripped_spruce_log[axis=y]")
    c.box(w // 2 + 1, w // 2 + 2, 1, 3, w - 3, w - 2, "stripped_spruce_log[axis=y]")
    c.box(w // 2 - 2, w // 2 + 2, 3, 4, w - 3, w - 2, "stripped_spruce_log[axis=x]")
    c.set(w // 2 - 1, 2, w - 2, f"{col}_wall_banner[facing=south]")
    for x, z in ((0, w - 1), (w - 1, w - 1), (0, 1), (w - 1, 2)):
        c.box(x, x + 1, 1, 3, z, z + 1, "spruce_fence")
    c.set(w - 2, 1, w - 1, "barrel[facing=up]")


def cart(c, w, st, col, T, ctx, supply=False):
    """A wagon with a cover in the player color. The draught animal is not part of the building."""
    x0, x1, z0, z1 = w // 2 - 1, w // 2 + 2, 2, w - 2
    for z in (z0, z1 - 1):                                 # wheels on both sides
        c.set(x0 - 1, 1, z, "spruce_trapdoor[facing=west,half=bottom,open=true]")
        c.set(x1, 1, z, "spruce_trapdoor[facing=east,half=bottom,open=true]")
    c.box(x0, x1, 1, 2, z0, z1, "spruce_slab[type=top]")
    c.box(w // 2, w // 2 + 1, 1, 2, z1, w, "oak_fence")       # shafts to the front
    if supply:
        c.box(x0, x1, 2, 3, z0, z1, "barrel[facing=up]")
        c.set(w // 2, 2, z0 + 1, "chest[facing=south]")
        c.box(x0, x1, 3, 4, z0, z1 - 1, f"{col}_carpet")
    else:
        c.box(x0, x0 + 1, 2, 4, z0, z1, f"{col}_wool"); c.box(x1 - 1, x1, 2, 4, z0, z1, f"{col}_wool")
        c.box(x0, x1, 4, 5, z0, z1, f"{col}_wool")
        c.set(w // 2, 2, z0, "hay_block")


def pavilion(c, w, st, col, T, ctx):
    """Like the game (#484): a round cloth tent with stripes in the player color, a yellow valance, a band in the
    player color under a white cone and a colored tip. A: wavy stripes, B: vertical stripes, C: the large pavilion
    (a low drum with diagonal stripes, a flat white roof and a pole with a flag)."""
    cx, r, m = (w - 1) / 2, w / 2 - 0.3, w // 2
    k = (ord(ctx.get("name", "PAVILION_A")[-1]) - ord("A")) % 3
    hw = 2 if k == 2 else 3                                             # wall height
    disc, X, Z = c.disc_mask(cx, cx, r)
    ring = disc & ~c.disc_mask(cx, cx, r - 1)[0]
    sec = np.floor((np.arctan2(Z - cx, X - cx) + math.pi) / (2 * math.pi) * 12).astype(int)    # 12 sectors around
    c.cylinder(cx, cx, r, 1, hw + 1, "white_wool", hollow=True)
    for y in range(1, hw + 1):
        stripe = [(y + sec // 2) % 2 == 0, sec % 2 == 0, (sec + y) % 2 == 0][k]
        c._fill_mask(ring & stripe, y, y + 1, f"{col}_wool")
    if k == 2:
        c.cylinder(cx, cx, r + 0.3, hw + 1, hw + 2, f"{col}_wool")     # the band at the edge of the flat roof
        c.cylinder(cx, cx, r - 0.7, hw + 1, hw + 2, "white_wool")
        top = hw + 2
        for rr in (r - 1.2, 0.8):
            c.cylinder(cx, cx, rr, top, top + 1, "white_wool" if rr > 1 else f"{col}_wool")
            top += 1
        if w >= 6:
            c.flag(m, top, m, col, 3)
    else:
        c._fill_mask(ring, hw + 1, hw + 2, "yellow_wool")               # the valance
        c.cylinder(cx, cx, r + 0.3, hw + 2, hw + 3, f"{col}_wool")
        top = hw + 3
        for rr in (r - 0.7, r - 1.7, r - 2.7):
            if rr > 0.3:
                c.cylinder(cx, cx, rr, top, top + 1, "white_wool")
                top += 1
        c.set(m, top, m, f"{col}_wool")                                 # the tip
    zd = int(cx + r)
    c.box(m, m + 1, 1, 3, zd, zd + 1, "air")                            # the door flap is open
    if w >= 6:                                                          # inside (#335): a carpet, a low table with a lamp, cushions
        c._fill_mask(c.disc_mask(cx, cx, r - 1)[0], 1, 2, f"{col}_carpet")
        c.box(m - 1, m + 1, 1, 2, m - 1, m, "spruce_slab[type=top,waterlogged=false]")
        c.set(m - 1, 2, m - 1, "lantern[hanging=false,waterlogged=false]")
        c.set(m - 1, 1, m - 2, "red_wool"); c.set(m, 1, m - 2, "red_wool")    # cushions at the back
        c.set(1, 1, m, "chest[facing=east,type=single,waterlogged=false]")


def yurt(c, w, st, col, T, ctx):
    """Like the game (#453): a low felt wall with a band, a flat dome roof and a wooden crown ring at the top.
    The variants A to M have blue felt with white zig-zags, or plain white felt with a blue zig-zag band."""
    cx = (w - 1) / 2
    r = w / 2 - 0.3
    k = ord(ctx.get("name", "YURT_A")[-1]) - ord("A")
    blue = "CHIEF" in ctx.get("name", "") or k % 3 != 2
    felt, trim = ("blue_wool", "white_wool") if blue else ("white_wool", "blue_wool")
    c.cylinder(cx, cx, r, 1, 4, felt, hollow=True)
    ring, X, Z = c.disc_mask(cx, cx, r)
    zig = ring & ((X + Z) % 2 == 0) & ~c.disc_mask(cx, cx, r - 1)[0]    # every second block: a zig-zag at this size
    c._fill_mask(zig, 2 + (not blue), 3 + (not blue), trim)             # blue: the middle band, white: the top band
    c.cylinder(cx, cx, r + 0.3, 4, 5, felt)                             # the dome: 3 discs, flat like the game
    c._fill_mask(c.disc_mask(cx, cx, r + 0.3)[0] & ~c.disc_mask(cx, cx, r - 0.7)[0] & ((X + Z) % 2 == 1), 4, 5, trim)
    c.cylinder(cx, cx, r - 0.7, 5, 6, felt)
    if w >= 6:
        c.cylinder(cx, cx, r - 1.9, 6, 7, felt)
        crown = "spruce_trapdoor[facing=north,half=top,open=false]" if blue else "brown_wool"     # tied hides
        c.box(w // 2 - 1, w // 2 + 1, 6, 7, w // 2 - 1, w // 2 + 1, crown)
    zd = int(cx + r)
    c.door(w // 2, 1, zd, "south", "spruce")
    if "CHIEF" in ctx.get("name", ""):
        c.flag(w // 2, 7 if w >= 6 else 6, w // 2, col)
    hearth_room(c, w, zd, col, ["red_carpet", "orange_carpet"], "chest[facing=south,type=single,waterlogged=false]")


def hearth_room(c, w, zd, col, rugs, store):
    """Inside of a round hut or yurt (#335): a hearth in the middle (its smoke goes up through the roof), rugs around
    it, a bed in the player color at the back and goods at the wall. The door is at (w // 2, zd)."""
    if w < 6:
        return
    m, air = w // 2, c.id("air")
    c.set(m - 1, 1, m - 1, "campfire[facing=south,lit=true,signal_fire=false,waterlogged=false]")
    for x in range(1, w - 1):
        for z in range(1, w - 1):
            if c.get(x, 1, z) == air and abs(x - m + 0.5) + abs(z - m + 0.5) <= 3:
                c.set(x, 1, z, rugs[(x + z) % len(rugs)])
    c.set(m - 1, 1, 1, f"{col}_bed[facing=east,occupied=false,part=foot]"); c.set(m, 1, 1, f"{col}_bed[facing=east,occupied=false,part=head]")
    c.set(1, 1, m, store); c.set(w - 2, 1, m - 1, "decorated_pot[cracked=false,facing=north,waterlogged=false]")
    c.box(m, m + 1, 1, 3, zd - 2, zd, "air")                            # the way from the door stays free


def hut(c, w, st, col, T, ctx):
    """Like the game (#483): a low wall of posts and wicker (some huts: mud), a steep thatch cone and a tuft of sticks.
    HUT_G is the large hut: a higher wall, a ledge in the roof and a blue clay finial."""
    cx, r = (w - 1) / 2, w / 2 - 0.5
    k = ord(ctx.get("name", "HUT_A")[-1]) - ord("A")
    big, hw = k == 6, 2 + (k == 6)                                      # wall height: the roof hangs low
    if k % 3 == 2:
        c.cylinder(cx, cx, r, 1, hw + 1, "packed_mud", hollow=True)
    else:
        c.cylinder(cx, cx, r, 1, hw + 1, "mangrove_roots[waterlogged=false]", hollow=True)    # wicker
        ring, X, Z = c.disc_mask(cx, cx, r)
        c._fill_mask(ring & ~c.disc_mask(cx, cx, r - 1)[0] & ((X + Z) % 2 == 0), 1, hw + 1, "spruce_log[axis=y]")
    radii = [r + 0.3, r - 0.9, r - 1.2, r - 1.9, r - 2.6] if big else [r + 0.3 - 0.7 * i for i in range(6)]
    y = hw + 1
    for rr in (rr for rr in radii if rr > 0.3):                         # steeper than one block per layer
        c.cylinder(cx, cx, rr, y, y + 1, "hay_block")
        y += 1
    m = w // 2
    if big:
        c.set(m, y, m, "blue_terracotta")
    else:
        c.set(m, y, m, "spruce_fence"); c.set(m - 1, y, m - 1, "spruce_fence")
    c.box(m, m + 1, 1, 3, w - 1, w, "air")
    hearth_room(c, w, w - 1, col, ["brown_carpet", "yellow_carpet"], "barrel[facing=up,open=false]")


def amphitheatre(c, w, st, col, T, ctx):
    cx = (w - 1) / 2
    R = w / 2 + 0.3
    h = max(8, round(w * 0.45))
    c.cylinder(cx, cx, R, 0, 1, "smooth_stone")
    c.cylinder(cx, cx, R, 1, h + 1, "smooth_sandstone", hollow=True)
    for y in range(2, h - 1, 4):                                        # rows of arches
        for k in range(0, 48):
            a = 2 * math.pi * k / 48
            if k % 2 == 0:
                x, z = int(round(cx + R * math.cos(a))), int(round(cx + R * math.sin(a)))
                c.box(x, x + 1, y, y + 2, z, z + 1, "air")
    rows = max(3, int(R) - 5)
    seats(c, cx, R, [max(2, h - 1 - i * (h - 2) // rows) for i in range(rows)], h, "polished_andesite")
    c.cylinder(cx, cx, R - 1 - rows, 0, 1, "sand")
    arena_inside(c, w, cx, col, stage=True)
    c.flag(w // 2, h + 1, 0, col, 3)


def seats(c, cx, R, tops, h, mat):
    """Rows of seats inside a round wall: row i goes up to tops[i] and steps down to the arena."""
    for i, t in enumerate(tops):
        c.cylinder(cx, cx, R - 1 - i, 1, t, mat)
        c.cylinder(cx, cx, R - 1 - i, t, h + 1, "air")
    c.cylinder(cx, cx, R - 1 - len(tops), 1, h + 1, "air")


def arena_inside(c, w, cx, col, stage=False):
    """Inside of a round arena (#451): a gate passage from the south, cells with iron bars under the seats
    (east and west), banners at the box of the emperor or behind a stage (north), and lanterns."""
    m = w // 2
    c.box(m - 1, m + 2, 1, 4, m, w + 1, "air")                          # the gate passage
    air = c.id("air")

    def edge(dx, dz):                                                    # the first seat block from the centre
        x, z = m, m
        while 0 < x < w - 1 and 0 < z < w - 1 and c.get(x, 1, z) == air:
            x, z = x + dx, z + dz
        return x, z
    xe, _ = edge(1, 0)
    xw, _ = edge(-1, 0)
    _, zn = edge(0, -1)
    if xe - xw < 4:                                                      # small sizes (--tile-size): no arena
        return
    lantern = "lantern[hanging=false,waterlogged=false]"
    items = [(x, 1, m + 1, lantern) for x in (xw + 1, xe - 1)]
    items += [(x, 2 if stage else 1, zn + 1, lantern) for x in (m - 2, m + 2 if stage else w + 1 - m)]
    items += [(m + dx, 3, z, "lantern[hanging=true,waterlogged=false]") for dx in (-1, 1)   # under the seats
              for z in range(m + 2, w - 2, 3) if c.get(m + dx, 4, z) != air]
    bars = "iron_bars[east=false,north=true,south=true,waterlogged=false,west=false]"
    for x, d in ((xe, 1), (xw, -1)):                                     # cells under the seats
        c.box(min(x, x + 2 * d), max(x, x + 2 * d) + 1, 1, 3, m - 1, m, "air")
        c.box(x, x + 1, 1, 3, m - 1, m, bars)
        items += [(x + 2 * d, 1, m - 1, lantern), (x + d, 1, m - 1, "hay_block[axis=y]")]
    if stage:                                                            # a wooden stage with props
        slab = "dark_oak_slab[type=bottom,waterlogged=false]"
        items = [(x, 1, z, slab) for x in range(xw + 1, xe) for z in (zn + 1, zn + 2)] + items
        items += [(m - 1, 2, zn + 2, "potted_fern"), (m + 1, 2, zn + 2, "flower_pot")]
        items += [(x, 2, zn + 1, f"{col}_wall_banner[facing=south]") for x in (m - 1, m + 1)]
    else:                                                                # the box of the emperor
        top = next(y for y in range(1, 64) if c.get(m, y, zn) == air)
        items += [(m, top, zn, "smooth_quartz_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]")]
        items += [(x, top, zn, "red_carpet") for x in (m - 1, m + 1)]
        items += [(x, top - 1, zn + 1, f"{col}_wall_banner[facing=south]") for x in (m - 1, m + 1)]
    c.furniture(items)


def monument(c, w, st, col, T, ctx):
    c.box(0, w, 0, 2, 0, w, "polished_andesite")
    c.box(1, w - 1, 2, 3, 1, w - 1, "smooth_stone")
    m = w // 2
    h = max(8, 3 * T)
    if w >= 5:
        c.box(m - 1, m + 2, 3, 4, m - 1, m + 2, "smooth_quartz")
    c.box(m, m + 1, 3, h, m, m + 1, "smooth_quartz")
    c.set(m, h, m, "gold_block")
    c.banner(m, 4, m + 1, col)


# --------------------------------------------------------------------------------------------
# Monuments and statues (AoE2 "other objects" that place_objects draws with these designs)
# --------------------------------------------------------------------------------------------
def buddha_statue(c, w, st, col, T, ctx, gold=False):
    """A seated Buddha on a lotus plinth: gold (A, B) or stone (C, D)."""
    body = "gold_block" if gold else "smooth_stone"
    m = w // 2
    c.box(m - 2, m + 2, 0, 1, m - 2, m + 2, "polished_andesite")
    c.box(m - 2, m + 2, 1, 2, m - 2, m + 2, "pink_terracotta")          # lotus
    c.box(m - 2, m + 2, 2, 3, m - 2, m + 1, body)                       # crossed legs
    c.box(m - 1, m + 1, 3, 5, m - 1, m + 1, body)                       # body
    c.box(m - 1, m + 1, 5, 6, m - 1, m + 1, body)                       # head
    c.set(m - 1, 6, m - 1, "smooth_stone_slab[type=bottom]" if not gold else "gold_block")    # hair knot


def statues(c, w, st, col, T, ctx):
    """Two standing temple statues of sandstone on plinths."""
    for x in (1, w - 2):
        m = w // 2
        c.box(x - 1, x + 2, 0, 2, m - 1, m + 2, "cut_sandstone")
        c.box(x, x + 1, 2, 4, m, m + 1, "smooth_sandstone")
        c.set(x, 4, m, "chiseled_sandstone")
        c.set(x, 5, m, "smooth_sandstone_slab[type=bottom]")


def stone_head(c, w, st, col, T, ctx):
    """A large carved stone head with eyes and a mouth to the south."""
    a, b = 1, w - 1
    c.box(a, b, 1, 6, a, b, "stone")
    c.box(a + 1, b - 1, 6, 7, a + 1, b - 1, "stone")
    c.box(a, b, 1, 2, a, b, "mossy_cobblestone")
    for x in (a + 1, b - 2):
        c.set(x, 4, b - 1, "polished_deepslate")                         # eyes
    c.box(a + 2, b - 2, 2, 3, b - 1, b, "polished_andesite")             # mouth
    c.set(w // 2, 3, b, "stone_button[face=wall,facing=south]")          # nose


def nine_bands(c, w, st, col, T, ctx):
    """The nine white horsetail banners of the Mongols: nine spears with white tassels."""
    for i in range(9):
        x, z = 1 + (i % 3) * (w - 3) // 2, 1 + (i // 3) * (w - 3) // 2
        h = 4 if i == 4 else 3
        c.box(x, x + 1, 1, 1 + h, z, z + 1, "oak_fence")
        c.set(x, 1 + h, z, "white_wool")
        c.set(x, 2 + h, z, "lightning_rod")


def small_pagoda(c, w, st, col, T, ctx):
    """A pagoda of the East Asian set."""
    pagoda(c, w, ARCH["east_asian"], col, T, ctx)


def torii(c, w, st, col, T, ctx):
    """A red torii gate on a stone slab, as in AoE2 DE: two pillars with black feet, a tie beam (nuki) that
    sticks out, a blue name plaque in the gap, and a top beam (kasagi) with a brown bark top and upturned ends."""
    m = w // 2
    c.box(0, w, 0, 1, 0, w, "smooth_stone")                             # the stone slab
    for x in (m - 2, m + 1):
        c.set(x, 1, m, "black_concrete")
        c.box(x, x + 1, 2, 6, m, m + 1, "red_concrete")
    c.box(m - 3, m + 3, 4, 5, m, m + 1, "red_concrete")                 # tie beam
    c.box(m - 1, m + 1, 5, 6, m, m + 1, "blue_stained_glass_pane[east=true,west=true]")   # name plaque
    c.box(m - 3, m + 3, 6, 7, m, m + 1, "red_concrete")
    c.box(m - 3, m + 3, 7, 8, m, m + 1, "spruce_planks")                # bark top
    c.set(m - 4, 7, m, "spruce_stairs[facing=west,half=bottom,shape=straight]")   # upturned ends
    c.set(m + 3, 7, m, "spruce_stairs[facing=east,half=bottom,shape=straight]")


def stupa(c, w, st, col, T, ctx):
    """A white Buddhist stupa: square terrace, dome, small box and a gold spire."""
    c.box(0, w, 0, 2, 0, w, "smooth_stone")
    c.box(1, w - 1, 2, 3, 1, w - 1, "smooth_quartz")
    m = (w - 1) / 2
    top = c.dome(m, m, w / 2 - 1.5, 3, "white_concrete")
    k = w // 2
    c.box(k - 1, k + 1, top + 1, top + 2, k - 1, k + 1, "smooth_quartz")
    c.box(k - 1, k, top + 2, top + 5, k - 1, k, "gold_block")
    c.set(k - 1, top + 5, k - 1, "lightning_rod")
    c.box(k - 1, k + 1, 1, 3, w - 1, w, "smooth_quartz_stairs[facing=north,half=bottom,shape=straight]")


def split_gate(c, w, st, col, T, ctx):
    """Trowulan split gate (candi bentar): two stepped towers of orange fired brick with a passage between them."""
    m = w // 2
    for x0, x1 in ((0, m - 1), (m + 1, w)):
        for k in range(4):
            c.box(x0 + (k if x0 else 0), x1 - (0 if x0 else k), 3 * k, 3 * k + 3, 2 + k // 2, w - 2 - k // 2, "resin_bricks")
        c.box(x0, x1, 3, 4, 2, w - 2, "chiseled_resin_bricks")           # carved band of the base
    c.box(m - 1, m + 1, 0, 1, 0, w, "resin_brick_slab[type=top]")


def rekha_deul(c, w, st, col, T, ctx):
    """An Odisha temple: a tall curved sandstone tower with a ribbed disc (amalaka) on top, and a porch."""
    c.box(0, w, 0, 1, 0, w, "cut_sandstone")
    a, b, y = 2, w - 2, 1
    for k in range(7):                                  # the tower narrows faster near the top
        h = 3 if k < 4 else 2
        c.box(a, b, y, y + h, a, b, "sandstone" if k % 2 == 0 else "cinnabar_bricks")    # red-painted bands
        y += h
        if k >= 2:
            a, b = a + 1 if b - a > 3 else a, b - 1 if b - a > 3 else b
    c.cylinder((w - 1) / 2, (w - 1) / 2, 1.6, y, y + 1, "chiseled_sandstone")
    c.set(w // 2, y + 1, w // 2, "gold_block"); c.set(w // 2, y + 2, w // 2, "lightning_rod")
    c.room(w // 2 - 2, w // 2 + 2, w - 3, w, 0, 3, "smooth_sandstone")
    c.box(w // 2 - 1, w // 2 + 1, 1, 3, w - 1, w, "air")
    if w >= 10:                                         # the sanctum (garbhagriha) in the tower behind the porch
        m, z0 = w // 2, 4
        c.box(m - 2, m + 2, 1, 4, z0, w - 3, "air")
        c.box(m - 1, m + 1, 1, 3, w - 3, w - 2, "air")
        candles = "candle[candles=3,lit=true,waterlogged=false]"
        items = [(m - 1, 1, z0, "chiseled_cinnabar"), (m, 1, z0, "chiseled_cinnabar"),   # the idol on its altar
                 (m - 1, 2, z0, "gold_block"), (m, 2, z0, "gold_block"),
                 (m - 2, 1, z0, candles), (m + 1, 1, z0, candles),
                 (m - 2, 1, z0 + 2, "potted_red_tulip"), (m + 1, 1, z0 + 2, "potted_orange_tulip")]
        items += [(x, 1, z, "orange_carpet") for x in (m - 1, m) for z in range(z0 + 1, w - 2)]
        c.furniture(items)
        hang(c, m - 1, 3, z0 + 2)


def svan_tower(c, w, st, col, T, ctx):
    """A Svan defense tower: tall, narrow, of rough stone, with a pitched tile roof."""
    h = max(12, 4 * T)
    c.room(0, w, 0, w, 0, h, "cobblestone")
    c.walls(0, w, 1, 2, 0, w, "mossy_cobblestone")
    c.door(w // 2, 1, w - 1)
    for y in range(4, h - 1, 4):
        c.set(w // 2, y, 0, "air"); c.set(w // 2, y, w - 1, "air")
    c.windows(0, w, 0, w, h - 1, b="air", step=2)
    c.gable(-1, w + 1, -1, w + 1, h + 1, "brick")
    if w < 4:
        return
    # inside (#441): a wooden floor under each row of windows and a ladder through them. The family and the hay
    # live at the bottom, stores, the hearth with its cauldron and a lookout above.
    a, b = 1, w - 1
    floors = list(range(5, h - 2, 4))
    for y in floors:
        c.box(a, b, y, y + 1, a, b, "spruce_planks")
    c.box(a, a + 1, 1, floors[-1] + 2, a, a + 1, "ladder[facing=south,waterlogged=false]")
    c.furniture([(b - 1, 1, a, "hay_block[axis=y]")])
    c.set(b - 1, 4, b - 1, "lantern[hanging=true,waterlogged=false]")
    rooms = [["chest[facing=west,type=single,waterlogged=false]", "barrel[facing=up,open=false]"],
             ["cauldron", "campfire[facing=north,lit=true,signal_fire=false,waterlogged=false]"],
             ["barrel[facing=up,open=false]", "lantern[hanging=false,waterlogged=false]"]]
    for k, y in enumerate(floors):                         # upper floors: the cells at the ladder stay free
        back, side = rooms[-1] if k == len(floors) - 1 else rooms[min(k, 1)]
        c.set(b - 1, y + 1, a, back); c.set(b - 1, y + 1, b - 1, side)
        if y + 4 < h and "lantern" not in side:
            c.set(a, y + 3, b - 1, "lantern[hanging=true,waterlogged=false]")


def courtyard_walls(c, w, st, col, T, ctx):
    """Low plastered walls around a paved courtyard, with an opening to the south."""
    c.box(0, w, 0, 1, 0, w, "smooth_sandstone")
    c.walls(0, w, 1, 3, 0, w, "sandstone")
    c.walls(0, w, 3, 4, 0, w, "sandstone_wall")
    c.box(w // 2 - 1, w // 2 + 1, 1, 4, w - 1, w, "air")
    c.set(w // 2, 1, w // 2, "decorated_pot[facing=south,cracked=false]")


def pillar(c, w, st, col, T, ctx):
    """A tall brick column with plants on top and vines on its sides."""
    m = w // 2
    h = 3 * T
    c.box(m - 1, m + 1, 1, 2, m - 1, m + 1, "mud_bricks")
    c.box(m, m + 1, 2, h, m, m + 1, "mud_bricks")
    c.set(m, h, m, "chiseled_sandstone")
    c.set(m, h + 1, m, "azalea_leaves[persistent=true]")
    for y in range(h - 3, h):
        c.set(m + 1, y, m, "vine[east=false,north=false,south=false,up=false,west=true]")


def garden(c, w, st, col, T, ctx):
    """A walled garden: a water channel in the middle, hedges, flowers and palms of leaves."""
    c.walls(0, w, 1, 2, 0, w, "mud_brick_wall")
    c.box(w // 2 - 1, w // 2 + 1, 1, 2, w - 1, w, "air")
    c.box(1, w - 1, 0, 1, w // 2, w // 2 + 1, "water[level=0]")
    for x in range(1, w - 1):
        for z in (1, w - 2):
            c.set(x, 1, z, "azalea_leaves[persistent=true]" if x % 3 else "flowering_azalea_leaves[persistent=true]")
        for z in (w // 2 - 2, w // 2 + 2):
            c.set(x, 1, z, ["poppy", "dandelion", "allium", "cornflower"][x % 4])
    for x in (2, w - 3):
        c.box(x, x + 1, 1, 4, w // 2 - 1, w // 2, "jungle_log[axis=y]")
        c.box(x - 1, x + 2, 4, 5, w // 2 - 2, w // 2 + 1, "jungle_leaves[persistent=true]")


def tomb(c, w, st, col, T, ctx):
    """A small mud brick tomb house with a wooden gable roof on a stepped platform."""
    c.box(0, w, 0, 1, 0, w, "mud_bricks")
    c.box(1, w - 1, 1, 2, 1, w - 1, "packed_mud")
    c.room(2, w - 2, 2, w - 2, 1, 3, "mud_bricks")
    c.door(w // 2, 2, w - 3)
    c.gable(1, w - 1, 1, w - 1, 5, "spruce", fill=(2, w - 2, 2, w - 2, "mud_bricks"))
    c.box(w // 2 - 1, w // 2 + 1, 1, 2, w - 1, w, stair("mud_brick_stairs", "north"))
    # the burial room: a stone sarcophagus at the back wall with candles and a grave pot, a rug at the door
    c.furniture([(3, 2, 3, "smooth_stone"), (w - 4, 2, 3, "smooth_stone"),
                 (3, 3, 3, "candle[candles=3,lit=true,waterlogged=false]"),
                 (w - 4, 3, 3, "decorated_pot[cracked=false,facing=south,waterlogged=false]")])
    for x in range(3, w - 3):
        if c.get(x, 2, w - 4) == c.id("air"):
            c.set(x, 2, w - 4, "red_carpet")


def burned_building(c, w, st, col, T, ctx):
    """The black ruin of a burned timber house: broken walls, fallen beams, smoke."""
    rng = c.rng
    a, b = 1, w - 1
    for x in range(a, b):
        for z in range(a, b):
            if x in (a, b - 1) or z in (a, b - 1):
                c.box(x, x + 1, 1, 1 + int(rng.integers(0, 4)), z, z + 1,
                      ["stripped_dark_oak_log[axis=y]", "blackstone", "coal_block", "dark_oak_log[axis=y]"][(x + z) % 4])
    c.box(a, b, 0, 1, a, b, "coarse_dirt")
    c.box(a + 1, b - 1, 3, 4, w // 2, w // 2 + 1, "dark_oak_log[axis=x]")    # one roof beam is left
    c.set(w // 2 - 1, 1, w // 2 - 1, "campfire[lit=true,signal_fire=false]")
    c.set(w // 2 + 1, 1, w // 2, "gravel")


def crane(c, w, st, col, T, ctx):
    """A Roman construction crane: a treadwheel, a tall mast with a jib, and a stone block on a chain."""
    m = w // 2
    h = max(8, 2 * w)
    c.box(1, w - 1, 0, 1, 1, w - 1, "spruce_planks")                       # base frame
    c.box(m, m + 1, 1, h, m, m + 1, "spruce_log[axis=y]")                  # mast
    for dx in (-1, 1):                                                     # stays to the ground
        c.set(m + dx, 1, m, "spruce_log[axis=y]")
        c.set(m + dx, 2, m, "spruce_fence")
    c.box(m, m + 1, h, h + 1, 1, w - 1, "stripped_spruce_log[axis=z]")     # jib
    c.box(m, m + 1, 4, h, 1, 2, "iron_chain[axis=y]")
    c.set(m, 3, 1, "chiseled_stone_bricks")                                # the load
    r = min(2.5, (w - 3) / 2)                                              # treadwheel at the back
    for k in range(24):
        a = 2 * math.pi * k / 24
        c.set(int(round(m + r * math.cos(a))), int(round(1 + r + r * math.sin(a))), w - 2, "stripped_spruce_log[axis=z]")
    c.box(m, m + 1, int(1 + r), int(2 + r), m + 1, w - 2, "spruce_log[axis=z]")    # axle to the mast


def scaffolding(c, w, st, col, T, ctx):
    """A house under construction: low stone walls in scaffolding with plank decks and a ladder."""
    a, b = 1, w - 1
    c.box(a, b, 0, 1, a, b, "coarse_dirt")
    c.walls(a + 1, b - 1, 1, 3, a + 1, b - 1, "cobblestone")
    c.box(a + 2, b - 2, 2, 3, b - 2, b - 1, "air")                         # the wall is not finished
    for x in (a, b - 1):
        for z in (a, b - 1):
            c.box(x, x + 1, 1, 7, z, z + 1, "scaffolding[bottom=false,distance=0,waterlogged=false]")
    for y in (3, 6):
        c.walls(a, b, y, y + 1, a, b, "spruce_slab[type=bottom,waterlogged=false]")
    c.box(a + 1, b - 1, 1, 6, b - 1, b, "air")
    c.box(w // 2, w // 2 + 1, 1, 7, b - 1, b, "ladder[facing=south,waterlogged=false]")
    c.set(b - 2, 1, a + 1, "stone_bricks")                                 # a pile of building stone
    c.set(b - 3, 1, a + 1, "stone_brick_slab[type=bottom,waterlogged=false]")


def scaffold_walk(c, w, st, col, T, ctx):
    """Scaffolding that units walk through: posts at the corners and a plank deck above head height."""
    a, b = 1, w - 1
    for x in (a, b - 1):
        for z in (a, b - 1):
            c.box(x, x + 1, 1, 6, z, z + 1, "scaffolding[bottom=false,distance=0,waterlogged=false]")
    c.box(a, b, 5, 6, a, b, "spruce_slab[type=bottom,waterlogged=false]")
    c.box(a, a + 1, 1, 5, w // 2, w // 2 + 1, "ladder[facing=east,waterlogged=false]")


def theatre(c, w, st, col, T, ctx):
    """A Greek theatre: a half circle of stone seats around a round floor, and a stage house in the south."""
    cx, cz = (w - 1) / 2, w * 0.6
    R, r0 = w * 0.55, w * 0.2
    xs = np.arange(w)
    for x in xs:
        for z in range(int(cz) + 1):
            d = math.hypot(x - cx, z - cz)
            if r0 + 1 <= d <= R:
                h = 1 + int((d - r0 - 1) * 0.8)                            # the seats rise outward
                c.box(x, x + 1, 1, h, z, z + 1, "stone_bricks")
                c.set(x, h, z, "smooth_stone_slab[type=bottom,waterlogged=false]" if h % 2 else "smooth_stone")
    c.cylinder(cx, cz, r0, 0, 1, "smooth_stone")                           # the orchestra
    c.set(int(cx), 1, int(cz), "chiseled_stone_bricks")                    # the altar
    for x in (int(cx), int(cx) + (w % 2 == 0)):                            # the aisle in the middle
        for z in range(int(cz - r0 - 1)):
            c.box(x, x + 1, 1, w, z, z + 1, "air")
            c.set(x, 0, z, "stone_bricks")
    z0 = w - 3                                                             # the stage house
    c.box(1, w - 1, 0, 1, z0 - 1, w, "smooth_quartz")
    c.box(2, w - 2, 1, 2, z0 - 1, z0, "spruce_planks")                     # the stage
    c.box(2, w - 2, 1, 6, z0 + 1, w - 1, "smooth_quartz")
    c.box(2, w - 2, 6, 7, z0 + 1, w - 1, "quartz_slab[type=bottom,waterlogged=false]")
    for x in range(2, w - 2, 3):
        c.box(x, x + 1, 2, 6, z0, z0 + 1, "quartz_pillar[axis=y]")
    c.box(w // 2 - 1, w // 2 + 1, 2, 4, z0 + 1, w - 1, "air")              # doors through the stage house
    c.door(w // 2, 1, w - 1)
    c.door(w // 2 - 1, 1, w - 1)
    c.banner(w // 2, 5, w - 1, col)


def stonehenge(c, w, st, col, T, ctx):
    """Stonehenge: a ring of standing stones with lintels, a horseshoe of tall trilithons and fallen stones."""
    cx = (w - 1) / 2
    R = w / 2 - 1.5
    stones = ["stone", "andesite", "stone", "tuff"]
    n = max(8, int(2 * math.pi * R / 2))
    for k in range(n):                                                     # the outer ring
        a = 2 * math.pi * k / n
        x, z = int(round(cx + R * math.cos(a))), int(round(cx + R * math.sin(a)))
        if k in (3, 4):                                                    # a fallen upright
            c.box(x, x + 1, 1, 2, z, z + 1, "mossy_cobblestone")
            continue
        c.box(x, x + 1, 1, 4, z, z + 1, stones[k % 4])
        if k not in (2, 5):
            for t in (0, 0.5):                                             # the lintel to the next stone
                b = 2 * math.pi * (k + t) / n
                c.set(int(round(cx + R * math.cos(b))), 4, int(round(cx + R * math.sin(b))), "stone")
    r = R * 0.55                                                           # the trilithons, open to the north-east
    for k, a in enumerate((0.6, 1.4, 2.2, 3.0, 3.8)):
        a += math.pi / 4
        x, z = int(round(cx + r * math.cos(a))), int(round(cx + r * math.sin(a)))
        c.box(x, x + 1, 1, 5, z, z + 1, "andesite")
        x2, z2 = int(round(cx + r * math.cos(a + 0.35))), int(round(cx + r * math.sin(a + 0.35)))
        c.box(x2, x2 + 1, 1, 5, z2, z2 + 1, "andesite")
        c.set(x, 5, z, "polished_andesite")
        c.set(x2, 5, z2, "polished_andesite")
    c.set(int(cx), 1, int(cx), "smooth_stone_slab[type=bottom,waterlogged=false]")    # the altar stone
    c.set(int(cx) + 1, 1, int(cx), "smooth_stone_slab[type=bottom,waterlogged=false]")
    c.box(w - 2, w - 1, 1, 3, 1, 2, "mossy_stone_bricks")                  # the heel stone


def church(c, w, st, col, T, ctx):
    """Landmark cathedrals: the wonder cathedral at this footprint."""
    cathedral(c, w, st, col, T, ctx)


# --------------------------------------------------------------------------------------------
# Variation, details, weathering and barriers (applied to every building)
# --------------------------------------------------------------------------------------------
PLASTER_ALT = {"white_terracotta": ["white_terracotta"] * 4 + ["calcite", "yellow_terracotta"],
               "smooth_sandstone": ["smooth_sandstone"] * 4 + ["cut_sandstone"],
               "smooth_red_sandstone": ["smooth_red_sandstone"] * 4 + ["cut_red_sandstone"],
               "terracotta": ["terracotta"] * 4 + ["brown_terracotta"],
               "smooth_stone": ["smooth_stone"] * 3 + ["polished_diorite", "stone"]}
ROOF_ALT = {"dark_oak": ["dark_oak"] * 3 + ["spruce", "deepslate_tile"],
            "deepslate_tile": ["deepslate_tile"] * 3 + ["dark_oak", "spruce"],
            "brick": ["brick"] * 4 + ["granite"],
            "spruce": ["spruce"] * 3 + ["dark_oak", "oak"]}
TIMBER_ALT = {"dark_oak_log": [("dark_oak_log", "stripped_dark_oak_log")] * 3 + [("spruce_log", "stripped_spruce_log")],
              "spruce_log": [("spruce_log", "stripped_spruce_log")] * 3 + [("dark_oak_log", "stripped_dark_oak_log")]}

TEXTURE = {   # block -> (variant, share). The main block stays the large majority, so the building stays recognizable.
    "stone_bricks": [("cracked_stone_bricks", .12), ("mossy_stone_bricks", .10), ("stone", .06), ("andesite", .03)],
    "stone_brick_stairs": [("mossy_stone_brick_stairs", .12), ("cobblestone_stairs", .04)],
    "stone_brick_slab": [("mossy_stone_brick_slab", .12)],
    "stone_brick_wall": [("mossy_stone_brick_wall", .15), ("cobblestone_wall", .08)],
    "mossy_stone_bricks": [("stone_bricks", .20), ("cracked_stone_bricks", .10), ("mossy_cobblestone", .08)],
    "cobblestone": [("mossy_cobblestone", .20), ("stone", .08), ("andesite", .06)],
    "polished_andesite": [("andesite", .15)],
    "white_terracotta": [("calcite", .18), ("diorite", .04)],
    "calcite": [("white_terracotta", .15), ("diorite", .05)],
    "yellow_terracotta": [("terracotta", .10), ("white_terracotta", .06)],
    "spruce_planks": [("dark_oak_planks", .08), ("stripped_spruce_wood", .06)],
    "oak_planks": [("stripped_oak_wood", .06), ("spruce_planks", .06)],
    "dark_oak_planks": [("spruce_planks", .08)],
    "smooth_sandstone": [("sandstone", .15), ("cut_sandstone", .10)],
    "cut_sandstone": [("sandstone", .12), ("smooth_sandstone", .12)],
    "sandstone": [("smooth_sandstone", .15), ("cut_sandstone", .08)],
    "smooth_red_sandstone": [("red_sandstone", .15), ("cut_red_sandstone", .10)],
    "cut_red_sandstone": [("red_sandstone", .15), ("smooth_red_sandstone", .10)],
    "mud_bricks": [("packed_mud", .15)],
    "terracotta": [("brown_terracotta", .08), ("packed_mud", .06)],
    "smooth_stone": [("stone", .15), ("andesite", .08)],
    "bricks": [("granite", .05)],
    "deepslate_tiles": [("cracked_deepslate_tiles", .12), ("deepslate_bricks", .06)],
    "deepslate_tile_stairs": [("deepslate_brick_stairs", .10)],
    "dark_oak_stairs": [("spruce_stairs", .12)],
    "spruce_stairs": [("dark_oak_stairs", .10)],
    "brick_stairs": [("granite_stairs", .06), ("mud_brick_stairs", .06)],
    "smooth_quartz": [("quartz_block", .15), ("calcite", .08)],
}

PROPS = ["barrel[facing=up]", "barrel[facing=up]", "hay_block", "composter", "lantern[hanging=false]",
         "potted_red_tulip", "oak_log[axis=x]", "spruce_log[axis=z]", "cauldron", "chest[facing=south]",
         "grindstone[face=floor,facing=north]", "pumpkin", "carved_pumpkin[facing=south]", "bee_nest[facing=south]",
         "stonecutter[facing=north]", "smoker[facing=south]", "beehive[facing=south]", "loom[facing=south]"]


def vary(st, rng):
    """A copy of the style with small random differences (plaster, roof and timber)."""
    import dataclasses
    pick = lambda opts: opts[int(rng.integers(len(opts)))]
    timber, beam = pick(TIMBER_ALT.get(st.timber, [(st.timber, st.beam)]))
    return dataclasses.replace(st, plaster=pick(PLASTER_ALT.get(st.plaster, [st.plaster])),
                               roof=pick(ROOF_ALT.get(st.roof, [st.roof])), timber=timber, beam=beam)


def decorate(c, fx, fz, chance=0.22):
    """Barrels, hay, firewood, lanterns and other things on free ground next to the walls."""
    a, m, b = c.a, c.m, c.below
    air = c.B("air")
    solid = lambda v: v not in (-1, air)
    keep_free = {(x + dx, z + dz) for x, z in c.doors for dx in (-1, 0, 1) for dz in (-1, 0, 1)}
    for x in range(fx):
        for z in range(fz):
            if (x, z) in keep_free or a[x + m, b + 1, z + m] != -1 or a[x + m, b + 2, z + m] != -1:
                continue
            near = any(0 <= x + dx < fx and 0 <= z + dz < fz and solid(a[x + dx + m, b + 1, z + dz + m])
                       for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if near and c.rng.random() < chance:
                c.set(x, 1, z, PROPS[int(c.rng.integers(len(PROPS)))])


def weather(c):
    """Mix similar blocks into walls, floors and roofs (moss, cracks, other stones and tiles)."""
    # Go in the order of the state names: the IDs depend on what was registered before (other conversions).
    # Take the cells from the original blocks, so each block is mixed one time only.
    orig = c.a.copy()
    for i in sorted(np.unique(orig[orig >= 0]), key=lambda i: c.B.states[i]):
        state = c.B.states[i]
        name = state.split(":")[1]
        base = name.split("[")[0]
        if base not in TEXTURE:
            continue
        cells = np.argwhere(orig == i)
        r = c.rng.random(len(cells))
        acc = 0.0
        for repl, share in TEXTURE[base]:
            pick = cells[(r >= acc) & (r < acc + share)]
            acc += share
            if len(pick):
                c.a[pick[:, 0], pick[:, 1], pick[:, 2]] = c.B("minecraft:" + repl + name[len(base):])


def rooms(c, fx, fz, y=0):
    """The local (x, z) of the free cells on the floor at local y (2 free blocks on the floor or the ground), the rooms
    (air) first, then nearest to the center: there the garrisoned units stand (#807). An open hall has no air, only
    free space (-1). An upper floor (y > 0) gives only room cells: the free space on a lower roof is outside."""
    m, b, air = c.m, c.below, c.B("air")
    sub = c.a[m:m + fx, b + y:b + y + 3, m:m + fz]
    free = (sub == -1) | (sub == air)
    xs, zs = np.nonzero((sub[:, 0] != air) & ((sub[:, 0] != -1) | (y == 0)) & free[:, 1] & free[:, 2])
    room = (sub[xs, 1, zs] == air) & (sub[xs, 2, zs] == air)
    if y:
        xs, zs, room = xs[room], zs[room], room[room]
    order = np.lexsort((zs, xs, (2 * xs - fx + 1) ** 2 + (2 * zs - fz + 1) ** 2, ~room))
    return [(int(xs[i]), int(zs[i])) for i in order]


def barriers(c, fx, fz, under=False):
    """Invisible barrier blocks in all free space of the footprint, up to 1 block above the building.
    Like in AoE2, nothing can walk into, through or over the building. under: units walk under it (the town center,
    #865): a column with 2 free blocks over the floor keeps its free space up to its first solid block."""
    m, b = c.m, c.below
    air = c.B("air")
    sub = c.a[m:m + fx, :, m:m + fz]
    used = np.nonzero((sub >= 0) & (sub != air))[1]
    if not len(used):
        return
    top = min(sub.shape[1], used.max() + 2)
    region = sub[:, b + 1:top, :]
    keep = np.zeros(region.shape, bool)
    if under:
        low = np.cumprod((region == air) | (region == -1), axis=1).astype(bool)    # free from the floor up
        keep = low & low[:, :2].all(1)[:, None, :]
        region[keep] = air                              # no plants in the passage
    region[(region == air) & ~keep] = c.B("barrier")    # inside the building: replaces anything (plants)
    region[(region == -1) & ~keep] = SOFT_BARRIER        # outside the walls: only fills free space




# --------------------------------------------------------------------------------------------
# Egyptian and other landmarks, wooden bridges, fish traps, ruins
# --------------------------------------------------------------------------------------------
def great_pyramid(c, w, st, col, T, ctx):
    """A true pyramid with smooth faces (stairs on every layer), a golden top and a passage to a burial chamber."""
    L = 0
    while w - 2 * L > 0:
        c.box(L, w - L, L, L + 1, L, w - L, "sandstone" if L % 3 else "smooth_sandstone")
        L += 1
    c.hip(0, w, 0, w, 0, "smooth_sandstone")                   # smooth outer faces
    top = (w - 1) // 2
    c.box(top, w - top, (w - 1) // 2, (w - 1) // 2 + 1, top, w - top, "gold_block")
    m = w // 2                                                  # entrance on the north side
    c.box(m - 1, m + 1, 2, 4, 2, 3, "air")
    c.set(m - 1, 1, 1, "chiseled_sandstone"); c.set(m, 1, 1, "chiseled_sandstone")
    r = w // 8
    if r < 2:
        return
    x0, x1, z0, z1, s = m - r, m + r + 1, m - r, m + r + 1, r            # burial chamber in the centre (#528)
    c.box(x0 - 1, x1 + 1, s - 1, s + 4, z0 - 1, z1 + 1, "polished_granite")
    c.box(x0, x1, s, s + 3, z0, z1, "air")
    y = 2                                                        # passage: level, then up a gallery of stairs
    for z in range(2, z0):
        if z0 - z <= s - 2:
            c.box(m - 1, m + 1, y, y + 1, z, z + 1, "sandstone_stairs[facing=south,half=bottom]")
            y += 1
        c.box(m - 1, m + 1, y, y + 3, z, z + 1, "air")
        if z == (2 + z0) // 2:
            c.set(m, y + 2, z, "lantern[hanging=true]")
    c.box(m, m + 1, s, s + 1, m - 1, m + 1, "polished_blackstone")                      # sarcophagus with a lid
    c.box(m, m + 1, s + 1, s + 2, m - 1, m + 1, "polished_blackstone_slab[type=bottom]")
    for x, z, b in ((x0, z1 - 1, "gold_block"), (x1 - 1, z1 - 1, "gold_block"),
                    (x0, z0, "decorated_pot[facing=south,cracked=false]"), (x1 - 1, z0, "decorated_pot[facing=south,cracked=false]"),
                    (x0, m, "lantern[hanging=false]"), (x1 - 1, m, "lantern[hanging=false]")):
        c.set(x, s, z, b)


def nubian_pyramid(c, w, st, col, T, ctx):
    """A steep Nubian pyramid with a small chapel in front."""
    for L in range(w // 2):
        c.box(L, w - L, 2 * L, 2 * L + 2, L, w - L, "sandstone" if L % 2 else "cut_sandstone")
    c.box(w // 2 - 1, w // 2 + 1, w, w + 1, w // 2 - 1, w // 2 + 1, "smooth_sandstone")
    m = w // 2
    c.box(m - 1, m + 1, 1, 4, w - 1, w + 1, "cut_sandstone")
    c.box(m - 1, m + 1, 1, 3, w, w + 1, "air")


def dome_rock(c, w, st, col, T, ctx):
    """Dome of the Rock: an octagonal building with blue tiles and a golden dome on a drum."""
    cx = (w - 1) / 2
    R = w / 2 - 0.4
    c.cylinder(cx, cx, R + 0.4, 0, 1, "smooth_stone")
    c.cylinder(cx, cx, R, 1, 4, "smooth_quartz", hollow=True)
    c.cylinder(cx, cx, R, 4, 7, "light_blue_terracotta", hollow=True)
    c.cylinder(cx, cx, R, 7, 8, "blue_terracotta", hollow=True)
    c.cylinder(cx, cx, R, 8, 9, "smooth_quartz")
    for y in (5,):
        for k in range(16):
            a = 2 * math.pi * k / 16
            c.set(int(round(cx + R * math.cos(a))), y, int(round(cx + R * math.sin(a))), "blue_stained_glass")
    r2 = max(2, w / 4)
    c.cylinder(cx, cx, r2, 9, 11, "light_blue_terracotta")
    top = c.dome(cx, cx, r2 + 0.3, 11, "gold_block")
    c.set(int(round(cx)), top + 1, int(round(cx)), "lightning_rod")
    m = int(round(cx))
    for x, z in ((m, 0), (m, w - 1), (0, m), (w - 1, m)):     # four doors
        c.box(x, x + 1, 1, 3, z, z + 1, "air")
        c.doors.append((x, z))
    # inside (#449): the rock on the floor in the middle, a ring of columns around it, carpets, candles and lanterns
    for x in range(w):
        for z in range(w):
            d = math.hypot(x - cx, z - cx)
            if d < max(1.2, w / 9):
                c.set(x, 1, z, c.rng.choice(["stone", "stone", "andesite", "tuff"]))
                if d < max(0.8, w / 14):
                    c.set(x, 2, z, c.rng.choice(["stone", "andesite"]))
    items = []
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8                          # off the door axes
        x, z = int(round(cx + w / 4 * math.cos(a))), int(round(cx + w / 4 * math.sin(a)))
        c.box(x, x + 1, 1, 8, z, z + 1, "quartz_pillar")
        x, z = int(round(cx + (R - 1.5) * math.cos(a))), int(round(cx + (R - 1.5) * math.sin(a)))
        items.append((x, 7, z, "lantern[hanging=true,waterlogged=false]"))
        x, z = int(round(cx + (w / 9 + 1) * math.cos(a))), int(round(cx + (w / 9 + 1) * math.sin(a)))
        items.append((x, 1, z, "candle[candles=3,lit=true,waterlogged=false]"))
    items += [(x, 1, z, "red_carpet") for x in range(w) for z in range(w) if w / 9 + 1.5 < math.hypot(x - cx, z - cx) < R - 0.5]
    c.furniture(items)
    c.banner(m + 1, 3, w, col)


def sankore(c, w, st, col, T, ctx):
    """Sankore Madrasah (Timbuktu): a mud-brick hall with a tapering tower full of wooden beams."""
    pl = "terracotta"
    c.room(0, w, 0, w, 0, 4, pl, "packed_mud", corner="brown_terracotta")
    c.walls(0, w, 1, 2, 0, w, "brown_terracotta")
    c.box(0, w, 5, 6, 0, w, "mud_bricks")
    for x in range(0, w, 2):
        c.set(x, 6, 0, "mud_brick_wall"); c.set(x, 6, w - 1, "mud_brick_wall")
    m = w // 2
    c.box(m, m + 1, 1, 3, w - 1, w, "air")
    c.doors.append((m, w - 1))
    # yellow ochre trim (#556): the cornice under the parapet and the frame of the door
    c.walls(0, w, 5, 6, 0, w, "polished_sulfur")
    c.box(m - 1, m + 2, 3, 4, w - 1, w, "chiseled_sulfur")
    for x in (m - 1, m + 1):
        c.box(x, x + 1, 1, 3, w - 1, w, "sulfur_bricks")
    # inside (#449): a school with bookshelves on the side walls, the teacher's lectern at the back, benches for
    # the students, chests of manuscripts and hanging lanterns
    lectern = "lectern[facing=south,has_book=true,powered=false]"
    items = [(x, y, z, "bookshelf") for x in (1, w - 2) for z in range(2, w - 3) for y in (1, 2)]
    items += [(1, 1, 1, "chest[facing=south,type=single,waterlogged=false]"), (w - 2, 1, 1, "chest[facing=south,type=single,waterlogged=false]"),
              (m, 1, 1, lectern), (m - 1, 1, 1, "candle[candles=2,lit=true,waterlogged=false]")]
    items += [(x, 1, z, stair("spruce_stairs", "south")) for z in range(3, w - 3, 2) for x in range(3, w - 3) if x != m]
    items += [(m, 1, z, "brown_carpet") for z in range(2, w - 1)]
    items += [(x, 4, z, "lantern[hanging=true,waterlogged=false]") for x in (2, w - 3) for z in (2, w - 3)]
    c.furniture(items)
    # tapering tower with beams that stick out
    a, b, y = m - 2, m + 2, 6
    while b - a >= 1 and y < 6 + 3 * w:
        c.box(a, b, y, y + 3, a, b, "mud_bricks")
        for x in range(a, b, 2):
            c.set(x, y + 1, a - 1, "stripped_oak_log[axis=z]"); c.set(x, y + 1, b, "stripped_oak_log[axis=z]")
        y += 3
        if y % 6 == 0:
            a, b = a + 1, b - 1
    c.set(m, y, m, "polished_sulfur_wall")
    c.banner(m + 1, 3, w, col)


def ring(c, cx, r, n, y0, y1, b):
    """n blocks on a circle (columns, posts). Returns their (x, z)."""
    out = []
    for k in range(n):
        a = 2 * math.pi * k / n
        x, z = int(round(cx + r * math.cos(a))), int(round(cx + r * math.sin(a)))
        c.box(x, x + 1, y0, y1, z, z + 1, b)
        out.append((x, z))
    return out


def arch_of_constantine(c, w, st, col, T, ctx):
    """Triumphal arch: a marble block with one large and two small arches, columns and an attic."""
    z0, z1 = w // 4, w - w // 4
    h = max(10, round(w * 0.9))
    c.box(0, w, 0, 1, z0 - 1, z1 + 1, "polished_andesite")
    c.box(0, w, 1, h, z0, z1, "smooth_quartz")
    c.box(0, w, h - 4, h - 3, z0 - 1, z1 + 1, "chiseled_quartz_block")       # cornice under the attic
    c.box(0, w, h, h + 1, z0, z1, "smooth_quartz_slab[type=bottom]")
    m, a = w // 2, max(2, w // 6)
    c.box(m - a, m + a, 1, h - 5, z0, z1, "air")                           # main arch
    s = max(1, (w - 2 * a - 4) // 2)                                       # side arches
    for x in (1, w - 1 - s):
        c.box(x, x + s, 1, (h - 5) * 2 // 3, z0, z1, "air")
    for z in (z0 - 1, z1):                                                 # columns on both faces
        for x in (0, m - a - 1, m + a, w - 1):
            c.box(x, x + 1, 1, h - 4, z, z + 1, "quartz_pillar")
    c.box(0, w, h - 2, h - 1, z1, z1 + 1, "red_terracotta")                 # painted band on the attic
    c.banner(m, h - 3, z1 + 1, col)


def colosseum(c, w, st, col, T, ctx):
    """Colosseum: a high ring of arcades, half of the top storey fallen, seats and a sand arena inside."""
    cx = (w - 1) / 2
    R = w / 2 - 0.2
    h = max(10, round(w * 0.7))
    c.cylinder(cx, cx, R, 0, 1, "smooth_stone")
    c.cylinder(cx, cx, R, 1, h, "smooth_sandstone", hollow=True)
    for y in range(1, h - 3, 4):
        c.cylinder(cx, cx, R, y + 3, y + 4, "cut_sandstone", hollow=True)   # cornices between the storeys
        for k in range(0, 40, 2):                                         # arcades
            a = 2 * math.pi * k / 40
            x, z = int(round(cx + R * math.cos(a))), int(round(cx + R * math.sin(a)))
            c.box(x, x + 1, y, y + 2, z, z + 1, "air")
    rows = max(3, int(R) - 4)
    seats(c, cx, R, [max(2, h - 3 - i * (h - 4) // rows) for i in range(rows)], h - 1, "sandstone")
    c.cylinder(cx, cx, R - 1 - rows, 0, 1, "sand")
    arena_inside(c, w, cx, col)
    m, X, Z = c.disc_mask(cx, cx, R + 1)
    c._fill_mask(m & (X + Z > w + 1), h - 4, h, "air")                      # the fallen part (front right)
    c.flag(w // 2, h, 0, col, 3)


def gol_gumbaz(c, w, st, col, T, ctx):
    """Gol Gumbaz: a cube with a very large dome and four octagonal towers with galleries and small domes."""
    h = max(8, round(w * 0.5))
    c.room(1, w - 1, 1, w - 1, 0, h, "smooth_sandstone", "smooth_stone", corner="cut_sandstone")
    c.walls(1, w - 1, 3, 4, 1, w - 1, "blue_terracotta")
    c.box(1, w - 1, h + 1, h + 2, 1, w - 1, "cut_sandstone")
    c.crenels(1, w - 1, 1, w - 1, h + 2, "sandstone_wall")
    cx = (w - 1) / 2
    c.cylinder(cx, cx, w / 2 - 3, h + 2, h + 3, "cut_sandstone")             # drum
    top = c.dome(cx, cx, w / 2 - 3, h + 3, "mud_bricks")
    c.set(w // 2, top + 1, w // 2, "gold_block"); c.set(w // 2, top + 2, w // 2, "lightning_rod")
    th = h + 5
    for tx in (1, w - 2):                                                 # corner towers
        for tz in (1, w - 2):
            c.cylinder(tx, tz, 1.5, 0, th, "cut_sandstone")
            for y in range(3, th, 3):
                c.cylinder(tx, tz, 1.5, y, y + 1, "smooth_sandstone_slab[type=bottom]")
            t2 = c.dome(tx, tz, 1.6, th, "mud_bricks")
            c.set(tx, t2 + 1, tz, "lightning_rod")
    m = w // 2                                                            # deep arched portal
    c.box(m - 2, m + 3, 1, h - 1, w - 2, w - 1, "blue_terracotta")
    c.box(m - 1, m + 2, 1, h - 2, w - 2, w - 1, "air")
    c.door(m, 1, w - 3, "south", "dark_oak")
    c.banner(m - 3, h - 2, w - 1, col); c.banner(m + 3, h - 2, w - 1, col)
    candles = "candle[candles=4,lit=true,waterlogged=false]"             # inside (#440): the tombs under the dome
    items = [(x, 1, z, "red_carpet") for x in range(m - 2, m + 3) for z in range(m - 3, m + 3)
             if abs(x - m) > 1 or abs(z - m) > 1]
    for x in (m - 1, m + 1):                                              # the sultan, his wife and his daughter
        items += [(x, 1, z, "smooth_quartz") for z in (m - 1, m)] + [(x, 2, z, "green_carpet") for z in (m - 1, m)]
    items += [(m, 1, m - 1, "smooth_quartz_slab[type=bottom,waterlogged=false]"), (m, 2, m - 1, "white_carpet")]
    items = [(x, 1, z, candles) for x in (m - 2, m + 2) for z in (m - 2, m + 1)] + items      # before the carpet
    items += [(x, 1, z, "lantern[hanging=false,waterlogged=false]") for x in (3, w - 4) for z in (3, w - 4)]
    c.furniture(items)


def sanchi_stupa(c, w, st, col, T, ctx):
    """Sanchi Stupa: a round terrace with a railing, a solid hemisphere, a square harmika with three umbrellas
    on top, and four stone gateways (toranas)."""
    cx = (w - 1) / 2
    R = w / 2 - 2
    c.cylinder(cx, cx, R + 1.5, 0, 1, "smooth_stone")
    c.cylinder(cx, cx, R, 1, 3, "cut_sandstone")
    ring(c, cx, R + 1, 48, 1, 2, "sandstone_wall")                        # ground railing
    ring(c, cx, R, 48, 3, 4, "sandstone_wall")                            # railing of the terrace
    top = c.dome(cx, cx, R - 1, 3, "smooth_sandstone")
    m = w // 2
    c.box(m - 1, m + 2, top + 1, top + 3, m - 1, m + 2, "sandstone_wall")  # harmika
    c.box(m, m + 1, top + 1, top + 6, m, m + 1, "stripped_oak_log")
    for y, r in ((top + 3, 1.6), (top + 4, 1.1), (top + 5, 0.6)):         # three umbrellas (chattra)
        c.cylinder(m, m, r, y, y + 1, "smooth_sandstone_slab[type=bottom]")
    for side in range(4):                                                 # toranas: two posts, three beams
        for d in (-2, 2):
            x, z = [(m + d, w - 1), (m + d, 0), (0, m + d), (w - 1, m + d)][side]
            c.box(x, x + 1, 1, 6, z, z + 1, "chiseled_sandstone")
        for y in (4, 5, 6):
            if side < 2:
                z = w - 1 if side == 0 else 0
                c.box(m - 3 + (y == 5), m + 4 - (y == 5), y, y + 1, z, z + 1, "cut_sandstone_slab[type=top]")
            else:
                x = 0 if side == 2 else w - 1
                c.box(x, x + 1, y, y + 1, m - 3 + (y == 5), m + 4 - (y == 5), "cut_sandstone_slab[type=top]")
    c.flag(m, top + 6, m + 1, col, 1)


def temple_of_heaven(c, w, st, col, T, ctx):
    """Temple of Heaven: a round hall on three white marble terraces, three blue conical roofs, a golden top."""
    cx = (w - 1) / 2
    R = w / 2 - 0.2
    for i in range(3):                                                    # terraces with railings
        r = R - 2 * i
        c.cylinder(cx, cx, r, i, i + 1, "smooth_quartz")
        ring(c, cx, r, 40, i + 1, i + 2, "diorite_wall")
    hr = R - 6
    y = 3
    c.cylinder(cx, cx, hr, y, y + 4, "red_terracotta", hollow=True)       # red hall with golden panels
    ring(c, cx, hr, 12, y, y + 4, "crimson_stem")
    for k, r in enumerate((hr + 1.5, hr + 0.5, hr - 0.5)):                # three blue roofs
        c.cylinder(cx, cx, r, y + 4, y + 5, "dark_prismarine")
        c.cylinder(cx, cx, r - 1, y + 5, y + 6, "dark_prismarine")
        if k < 2:
            c.cylinder(cx, cx, r - 1.5, y + 6, y + 8, "red_terracotta")
            ring(c, cx, r - 1.5, 8, y + 6, y + 8, "gold_block")
        y += 4
    top = c.cone(cx, cx, hr - 2.5, y + 2, "dark_prismarine")
    m = w // 2
    c.set(m, top + 1, m, "gold_block"); c.set(m, top + 2, m, "lightning_rod")
    for i in range(3):                                                    # stairs to the door
        c.box(m - 1, m + 2, i, i + 1, int(cx + R - 2 * i), w, stair("quartz_stairs", "north"))
        c.box(m - 1, m + 2, i + 1, i + 2, int(cx + R - 2 * i), w, "air")
    c.box(m, m + 1, 3, 6, int(cx + hr), int(cx + hr) + 1, "air")
    c.door(m, 3, int(cx + hr), "south", "dark_oak")
    c.banner(m - 2, 5, int(cx + hr) + 1, col)
    x, zb = reach(c, m, 3, m, 0, -1)                                      # inside (#440): a golden altar for the tablets
    items = [(m, 3, zb, "gold_block"), (m, 4, zb, "candle[candles=3,lit=true,waterlogged=false]"),
             (m - 1, 3, zb, "red_terracotta"), (m + 1, 3, zb, "red_terracotta"),
             (m - 1, 4, zb, "lantern[hanging=false,waterlogged=false]"),
             (m + 1, 4, zb, "lantern[hanging=false,waterlogged=false]")]
    items += [(x, 3, z, "yellow_carpet" if (x, z) == (m, m) else "red_carpet")
              for x in range(m - 2, m + 3) for z in range(m - 2, m + 3)]
    c.furniture(items)


def minaret_of_jam(c, w, st, col, T, ctx):
    """Minaret of Jam: a very tall round minaret with blue bands and balconies next to a courtyard with domes."""
    a, b = 0, w - 4
    c.room(a, b, a + 4, w, 0, 4, "smooth_sandstone", "smooth_sandstone", corner="cut_sandstone")
    c.walls(a, b, 1, 2, a + 4, w, "blue_terracotta")
    c.box(a + 3, b - 3, 1, 5, a + 7, w - 3, "air")                        # open courtyard
    c.box(a + 3, b - 3, 0, 1, a + 7, w - 3, "smooth_stone")
    c.walls(a, b, 4, 5, a + 4, w, "smooth_sandstone")
    for x in range(a + 1, b - 1, 2):                                       # small domes on the roof
        for z in (a + 5, w - 2):
            c.set(x, 5, z, "smooth_sandstone_slab[type=bottom]")
    for z in range(a + 6, w - 2, 2):
        for x in (a + 1, b - 2):
            c.set(x, 5, z, "smooth_sandstone_slab[type=bottom]")
    m = (a + b) // 2
    c.box(m - 1, m + 2, 1, 4, w - 1, w, "air")
    c.box(m - 2, m + 3, 4, 6, w - 1, w, "light_blue_terracotta")            # portal
    tx, tz = w - 2.5, 2.5                                                 # the minaret
    H = max(24, round(w * 2.2))
    c.cylinder(tx, tz, 2.2, 0, 2, "smooth_sandstone")
    c.cylinder(tx, tz, 2.0, 2, H // 2, "cut_sandstone")
    c.cylinder(tx, tz, 1.6, H // 2, H, "cut_sandstone")
    for y in range(4, H, 5):
        c.cylinder(tx, tz, 2.0 if y < H // 2 else 1.6, y, y + 1, "blue_terracotta")
    for y in (H // 2, 3 * H // 4, H):                                     # balconies
        c.cylinder(tx, tz, 2.6, y, y + 1, "smooth_sandstone_slab[type=bottom]")
    c.cylinder(tx, tz, 1.1, H + 1, H + 3, "cut_sandstone")
    top = c.dome(tx, tz, 1.1, H + 3, "smooth_quartz")
    c.set(int(tx), top + 1, int(tz), "lightning_rod")
    if w >= 8:                                                            # a spiral stair up to the top balcony
        i, j = int(tx), int(tz)                                           # the shaft is 2 x 2 blocks
        c.box(i, i + 2, 1, H + 1, j, j + 2, "air")
        c.door(i, 1, j + 2, wood="jungle")
        steps = [(i + 1, j + 1, "east"), (i + 1, j, "north"), (i, j, "west"), (i, j + 1, "south")]
        for y in range(1, H):                                             # one turn every 4 blocks: 3 blocks headroom
            x, z, f = steps[(y - 1) % 4]
            c.set(x, y, z, stair("smooth_sandstone_stairs", f))
            if y % 6 == 0:
                c.set(x, y - 1, z, "lantern[hanging=true]")             # under the stair, over the head
        for y in (H - 2, H - 1):                                          # out through the drum onto the balcony
            x, z, f = steps[(y - 1) % 4]
            c.box(x, x + 1, H, H + 3, z, z + 1, "air")
    c.banner(m, 3, w, col)


def oracles_temple(c, w, st, col, T, ctx):
    """Greek temple of an oracle: steps, a ring of marble columns, a closed cella and a tiled gable roof."""
    for i in range(2):
        c.box(i, w - i, i, i + 1, i, w - i, "smooth_quartz")
    a, b = 2, w - 2
    h = max(6, round(w * 0.45))
    for x in range(a, b, 2):                                              # peristyle
        for z in (a, b - 1):
            c.box(x, x + 1, 2, 2 + h, z, z + 1, "quartz_pillar")
    for z in range(a, b, 2):
        for x in (a, b - 1):
            c.box(x, x + 1, 2, 2 + h, z, z + 1, "quartz_pillar")
    c.room(a + 2, b - 2, a + 2, b - 3, 1, h + 1, "smooth_quartz", "smooth_quartz")
    c.box(a - 1, b + 1, 2 + h, 3 + h, a - 1, b + 1, "chiseled_quartz_block")   # entablature
    c.gable(a - 1, b + 1, a - 1, b + 1, 3 + h, "brick", fill=(a - 1, b + 1, a - 1, b + 1, "smooth_quartz"),
            axis="z")
    m = w // 2
    c.box(m, m + 1, 2, 5, b - 4, b - 3, "air")
    c.door(m, 2, b - 4, "south", "dark_oak")
    c.set(m - 1, 2, b - 2, "campfire[lit=true,facing=south]")              # the oracle's fire
    c.banner(m + 1, 4, b - 3, col)
    x0, x1, z0, z1 = a + 3, b - 3, a + 3, b - 4                            # inside the cella (#440)
    pot = "decorated_pot[cracked=false,facing=south,waterlogged=false]"
    candles = "candle[candles=3,lit=true,waterlogged=false]"
    c.furniture([(m, 2, z0, "chiseled_quartz_block"), (m, 3, z0, "quartz_pillar"), (m, 4, z0, "gold_block"),
                 (m - 1, 2, z0, candles), (m + 1, 2, z0, candles),             # the statue of the god
                 (m, 2, z0 + 1, "cauldron"),                                    # the oracle's tripod
                 (x0, 2, z0, pot), (x1 - 1, 2, z0, pot), (x0, 2, z1 - 1, pot), (x1 - 1, 2, z1 - 1, pot),
                 (x0, 2, (z0 + z1) // 2, "lantern[hanging=false,waterlogged=false]"),
                 (x1 - 1, 2, (z0 + z1) // 2, "lantern[hanging=false,waterlogged=false]")])


def mosque_landmark(c, w, st, col, T, ctx):
    """A mosque: always the middle eastern model, whatever the civilization of the player."""
    mosque(c, w, ARCH["middle_eastern"], col, T, ctx)


def hall_of_heroes(c, w, st, col, T, ctx):
    """Hall of Heroes: a three-storey round pavilion with blue pillars, flared tiled roofs and a golden dragon."""
    cx = (w - 1) / 2
    R = w / 2 - 1
    c.cylinder(cx, cx, R + 0.8, 0, 2, "stone_bricks")
    ring(c, cx, R + 0.8, 40, 2, 3, "stone_brick_wall")
    y, r = 2, R - 1
    for i in range(3):
        c.cylinder(cx, cx, r, y, y + 4, "dark_oak_planks", hollow=True)
        ring(c, cx, r, 8, y, y + 4, "lapis_block")
        ring(c, cx, r, 16, y + 2, y + 3, "glass_pane")
        c.cylinder(cx, cx, r + 2, y + 4, y + 5, "deepslate_tile_slab[type=bottom]")    # flared eaves
        c.cylinder(cx, cx, r + 1, y + 5, y + 6, "deepslate_tiles")
        y, r = y + 6, r - 1.5
    top = c.cone(cx, cx, r + 1.5, y, "deepslate_tiles")
    m = w // 2
    c.set(m, top + 1, m, "gold_block"); c.set(m, top + 2, m, "lightning_rod")
    for k in range(28):                                                   # the dragon winds up the hall
        a = 2 * math.pi * k / 10
        rr = R - 1 + 1 - k * 4.5 / 28
        c.set(int(round(cx + rr * math.cos(a))), 4 + k // 2, int(round(cx + rr * math.sin(a))), "gold_block")
    c.box(m - 1, m + 2, 1, 2, w - 1, w, stair("stone_brick_stairs", "north"))
    c.box(m, m + 1, 2, 5, int(cx + R - 1), w - 1, "air")
    c.door(m, 2, int(cx + R - 1), "south", "dark_oak")
    for x in (m - 2, m + 2):                                              # guardian lions
        c.set(x, 2, w - 2, "chiseled_stone_bricks")
    c.banner(m - 1, 4, int(cx + R), col)
    _, zb = reach(c, m, 2, m, 0, -1)                                      # inside (#440): a bronze hero at the back
    lantern = "lantern[hanging=false,waterlogged=false]"
    items = [(m, 2, zb, "chiseled_stone_bricks"), (m, 3, zb, "waxed_copper_block"), (m, 4, zb, "waxed_cut_copper"),
             (m - 1, 2, zb, "candle[candles=4,lit=true,waterlogged=false]"),
             (m + 1, 2, zb, "candle[candles=4,lit=true,waterlogged=false]")]
    items += [(m, 2, z, f"{col}_carpet") for z in range(zb + 1, int(cx + R - 1))]
    for d in (-1, 1):
        items.append((reach(c, m, 2, m, d, 0)[0], 2, m, lantern))
        items.append((reach(c, m, 2, m - 2, d, 0)[0], 2, m - 2,
                      f"chest[facing={'east' if d < 0 else 'west'},type=single,waterlogged=false]"))
        x, z = reach(c, m + 2 * d, 4, m, 0, -1)
        items.append((x, 4, z, f"{col}_wall_banner[facing=south]"))
    items += [(m, y, m, lantern) for y in (8, 14)]                         # light on the upper floors
    c.furniture(items)


def shrine(c, w, st, col, T, ctx):
    """A small temple: a plinth, a cella with a door and a stepped tower (shikhara) with a golden top."""
    c.box(0, w, 0, 1, 0, w, "smooth_sandstone")
    a, b = 1, w - 1
    c.room(a, b, a, b, 0, 4, "cut_sandstone", "smooth_sandstone", corner="chiseled_sandstone")
    m = w // 2
    c.box(m - 1, m + 1, 1, 4, b - 1, b, "air")
    c.box(m - 2, m + 2, 4, 5, b - 1, b + 1, "smooth_sandstone_slab[type=bottom]")   # porch roof
    top = c.spire(a, b, a, b, 5, "sandstone", steep=2, tip="gold_block")
    c.set(m, top + 1, m, "lightning_rod")
    c.banner(m + 1, 3, b, col)
    candles, lantern = "candle[candles=3,lit=true,waterlogged=false]", "lantern[hanging=false,waterlogged=false]"
    z0, z1 = a + 1, b - 3                             # the cella; the row b - 2 behind the opening stays free
    items = [(m, 1, z0, "chiseled_sandstone"), (m, 2, z0, "gold_block"),     # the idol on its altar
             (m - 1, 1, z0, candles), (m + 1, 1, z0, candles)]
    items += [(m, 1, z, f"{col}_carpet") for z in range(z0 + 1, b - 1)]
    for x in (a + 1, b - 2):                                               # offerings and light at the side walls
        items += [(x, 1, z0 + 1, "potted_poppy"), (x, 1, z1, lantern)]
    c.furniture(items)


def pagan_shrine(c, w, st, col, T, ctx):
    """Pagan shrine: a sacred oak tree in a ring of wooden frames, carved posts with ribbons and stones."""
    cx = (w - 1) / 2
    m = w // 2
    c.cylinder(cx, cx, w / 2, 0, 1, "coarse_dirt")
    c.box(m - 1, m + 1, 1, 6, m - 1, m + 1, "oak_log")                      # thick trunk
    for dy, r in ((6, 3.5), (7, 4.5), (8, 4.5), (9, 4), (10, 3), (11, 1.5)):
        c.cylinder(cx, cx, r, dy, dy + 1, "oak_leaves[persistent=true]")
    for x, z in ((1, 1), (w - 2, 1), (1, w - 2), (w - 2, w - 2)):          # wooden frames at the corners
        c.box(x, x + 1, 1, 4, z, z + 1, "spruce_log")
        c.set(x, 4, z, "spruce_fence")
    for x in (2, w - 3):
        c.box(x, x + 1, 3, 4, 1, w - 1, "spruce_log[axis=z]")
        for z in range(3, w - 3, 3):
            c.set(x, 2, z, f"{col}_wool")
    for x, z in ((0, m), (w - 1, m), (m - 3, 0), (m + 3, w - 1)):           # carved posts
        c.box(x, x + 1, 1, 4, z, z + 1, "stripped_oak_log")
        c.set(x, 2, z, f"{col}_wool")
    for x, z in ((3, w - 2), (w - 4, 2), (m + 3, 3)):
        c.set(x, 1, z, "cobblestone")
    c.banner(m, 3, w - 1, col)
    skull = "skeleton_skull[powered=false,rotation=0]"
    items = [(m, 1, m + 2, "mossy_cobblestone"), (m, 2, m + 2, skull),         # the offering stone at the tree
             (m - 1, 1, m + 2, "candle[candles=4,lit=true,waterlogged=false]"),
             (m + 1, 1, m + 2, "potted_red_mushroom"),
             (m, 1, w - 2, "campfire[facing=south,lit=true,signal_fire=false,waterlogged=false]"),
             (m - 3, 4, 0, skull), (m + 3, 4, w - 1, skull)]                 # skulls on the carved posts
    items += [(x, 2, z, "lantern[hanging=true,waterlogged=false]") for x in (2, w - 3) for z in (4, w - 4)]
    empty = (-1, c.id("air"))                                              # an open place: no room, no door
    for x, y, z, b in items:
        if c.get(x, y, z) in empty:
            c.set(x, y, z, b)


def wooden_bridge(c, w, st, col, T, ctx):
    """One tile of a wooden bridge: a deck of boards across the bridge on piles. Like the game, no railings:
    on open water sides the piles rise over the deck as posts, every second block."""
    deck, along_z = ctx["deck"], ctx.get("along_z", False)
    for k in range(w):                                    # boards across the bridge: the seams show the direction
        board = "spruce_planks" if k % 2 else f"stripped_spruce_log[axis={'x' if along_z else 'z'}]"
        if along_z:
            c.box(0, w, deck, deck + 1, k, k + 1, board)
        else:
            c.box(k, k + 1, deck, deck + 1, 0, w, board)
    for x, z in ((0, 0), (w - 1, 0), (0, w - 1), (w - 1, w - 1)):
        c.box(x, x + 1, -10, deck, z, z + 1, "stripped_oak_log")
    for side in ctx.get("rails", ()):
        for k in range(0, w, 2):
            x, z = {"n": (k, 0), "s": (k, w - 1), "w": (0, k), "e": (w - 1, k)}[side]
            c.box(x, x + 1, -10, deck + 2, z, z + 1, "stripped_oak_log")


def fish_trap(c, w, st, col, T, ctx):
    """A fish trap like the game model: a basket tunnel on the water. Long bamboo rods along x on three
    half-round hoops (dark ends, a light middle hoop), held by stakes at the feet of the hoops (#486)."""
    cz, r = (w - 1) / 2, max(1.5, (w - 1) / 2 - 2)
    def ring(angles):                                                            # (z, y) cells, symmetric to z = cz
        half = {(int(cz + r * math.cos(a) + 0.5), int(r * math.sin(a) + 0.5)) for a in angles}
        return sorted(half | {(w - 1 - z, y) for z, y in half})
    arc = ring(np.linspace(0, math.pi / 2, 2 * w))
    for z, y in ring(np.linspace(0, math.pi / 2, 4)):                            # the rods, from end to end
        c.box(0, w, y, y + 1, z, z + 1, "bamboo_fence")
    for x, b in ((1, "dark_oak_wood[axis=x]"), (w // 2, "stripped_oak_wood[axis=x]"), (w - 2, "dark_oak_wood[axis=x]")):
        for z, y in arc:
            c.set(x, y, z, b)
        for z in (arc[0][0], arc[-1][0]):                                        # stakes in the bed
            c.box(x, x + 1, -6, 0, z, z + 1, "dark_oak_fence")


# Sets of designs (defined after all designs)
LANDMARKS = {arch_of_constantine, colosseum, gol_gumbaz, sanchi_stupa, temple_of_heaven, minaret_of_jam, oracles_temple,
             mosque_landmark, hall_of_heroes, shrine, pagan_shrine}
MONUMENTAL = LANDMARKS | {theatre, stonehenge, mole, harbor_chain, flagship, helepolis, great_pyramid, nubian_pyramid, dome_rock, sankore, wooden_bridge, fish_trap, wonder, castle, krepost, monastery, church, amphitheatre, monument, wall_segment, gate, tower,
              bridge, aqueduct}
NO_PROPS = LANDMARKS | {torii, theatre, stonehenge, crane, scaffold_walk, shipyard, port, mole, harbor_chain, flagship, helepolis, great_pyramid, nubian_pyramid, dome_rock, wooden_bridge, fish_trap, barricade, wall_segment, gate, bridge, aqueduct, tower, outpost, wonder, dock, harbor, monument, amphitheatre}


def building_rect(o):
    """Footprint of a building in tiles: (x0, x1, y0, y1)."""
    size = footprint(o["name"])
    if "GATE" in o["name"]:
        size = 1
    return o["x"] - size / 2, o["x"] + size / 2, o["y"] - size / 2, o["y"] + size / 2


def drop_covered(objects):
    """Skip a building when more than 80% of it lies under one larger building (for example a wonder
    that the scenario author hid under the Great Pyramid). Returns (objects, number skipped)."""
    blds = [(o, building_rect(o)) for o in objects if o["kind"] == "B" and footprint(o["name"]) >= 2]
    skip = set()
    for o, (a0, a1, b0, b1) in blds:
        area = (a1 - a0) * (b1 - b0)
        for p, (c0, c1, d0, d1) in blds:
            if p is o or (c1 - c0) * (d1 - d0) <= area or id(p) in skip:
                continue
            ov = max(0, min(a1, c1) - max(a0, c0)) * max(0, min(b1, d1) - max(b0, d0))
            if ov > 0.8 * area:
                skip.add(id(o))
                break
    return [o for o in objects if id(o) not in skip], len(skip)


def footprint_mask(objects, cols):
    """Block columns covered by buildings (not farms)."""
    T, n = cols.T, cols.n
    mask = np.zeros((n, n), bool)
    for o in objects:
        if o["kind"] != "B" or "FARM" in o["name"] or "RUINS" == o["name"]:
            continue
        x0, x1, y0, y1 = building_rect(o)
        if "GATE" in o["name"]:
            x0, x1, y0, y1 = o["x"] - 2, o["x"] + 2, o["y"] - 2, o["y"] + 2
        mask[max(0, int(round(x0 * T))):max(0, min(n, int(round(x1 * T)))),
             max(0, int(round(y0 * T))):max(0, min(n, int(round(y1 * T))))] = True
    return mask
