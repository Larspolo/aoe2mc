#!/usr/bin/env python3
"""
Make synthetic AoE2 DE scenarios for tests (no real map files necessary).

Usage:
    python tools/scenarios.py tiny OUT.aoe2scenario
    python tools/scenarios.py gallery OUT.aoe2scenario [--kinds BOU]
    python tools/scenarios.py stress|buildings|units|village|facing|river OUT.aoe2scenario

tiny:      24x24 tiles with land, shallow and deep water, a hill, buildings, units, a tree, a mine and fish.
gallery:   every object type of the parser in a grid (B = buildings, O = other objects, U = units).
stress:    units against every side of buildings, trees, mines, cliffs and a mountain; on slopes and on a bridge.
buildings: every building type for 8 civilizations with different architecture sets (players 1-8).
units:     every land unit on land and every ship on water.
village:   a small map with terrain types, water, a hill, a town and animals.
river:     a river at elevation 2 between land at elevation 2, with a dock, a bridge, a ship and fish (#165).
facing:    units at the rotations 0, pi/4 ... 7pi/4, to compare the facing in AoE2 and in Minecraft (docs/facing.md).
"""
import argparse
import contextlib
import io
import math
import os
import sys

from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.object_support import Civilization
from AoE2ScenarioParser.datasets.other import OtherInfo
from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.datasets.terrains import TerrainId
from AoE2ScenarioParser.datasets.units import UnitInfo
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import units  # noqa: E402

# One civilization per architecture set (players 1-8)
CIVS = [Civilization.BRITONS, Civilization.GOTHS, Civilization.SPANISH, Civilization.PERSIANS,
        Civilization.HINDUSTANIS, Civilization.MALIANS, Civilization.JAPANESE, Civilization.AZTECS]


def new_scenario(size):
    with contextlib.redirect_stdout(io.StringIO()):     # the parser prints a lot of status text
        scn = AoE2DEScenario.from_default()
    scn.map_manager.map_size = size
    return scn


def save(scn, path):
    with contextlib.redirect_stdout(io.StringIO()):
        scn.write_to_file(path)
    return path


def tiny(path, texts=None):
    """texts: {"instructions": "...", ...} for the message tab (the book at the spawn)."""
    scn = new_scenario(24)
    for k, v in (texts or {}).items():
        setattr(scn.message_manager, k, v)
    for t in scn.map_manager.terrain:
        if t.x >= 20:
            t.terrain_id = TerrainId.WATER_DEEP
        elif t.x >= 18:
            t.terrain_id = TerrainId.WATER_SHALLOW
        elif 3 <= t.x <= 6 and 3 <= t.y <= 6:
            t.elevation = 2
    um = scn.unit_manager
    um.add_unit(PlayerId.ONE, BuildingInfo.TOWN_CENTER.ID, x=12, y=12)
    um.add_unit(PlayerId.ONE, BuildingInfo.HOUSE.ID, x=4, y=16)
    um.add_unit(PlayerId.TWO, BuildingInfo.BARRACKS.ID, x=14.5, y=4.5)
    um.add_unit(PlayerId.ONE, UnitInfo.KNIGHT.ID, x=10.5, y=16.5)
    um.add_unit(PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=11.5, y=17.5)
    um.add_unit(PlayerId.TWO, UnitInfo.ARCHER.ID, x=8.5, y=8.5)
    um.add_unit(PlayerId.GAIA, UnitInfo.SHEEP.ID, x=7.5, y=19.5)
    um.add_unit(PlayerId.GAIA, OtherInfo.TREE_OAK.ID, x=2.5, y=20.5)
    um.add_unit(PlayerId.GAIA, OtherInfo.GOLD_MINE.ID, x=16.5, y=20.5)
    um.add_unit(PlayerId.GAIA, OtherInfo.FISH_TUNA.ID, x=22.5, y=12.5)
    return save(scn, path)


def gallery(path, kinds="BOU", step=7):
    groups = [("B", BuildingInfo, PlayerId.ONE), ("O", OtherInfo, PlayerId.GAIA), ("U", UnitInfo, PlayerId.TWO)]
    items = [(e, player) for k, enum, player in groups if k in kinds for e in enum]
    per_row = 30
    rows = -(-len(items) // per_row)
    scn = new_scenario(max(24, max(per_row, rows) * step + 8))
    um = scn.unit_manager
    for i, (e, player) in enumerate(items):
        x, y = 4 + (i % per_row) * step, 4 + (i // per_row) * step
        um.add_unit(player, e.ID, x=x + 0.5, y=y + 0.5)
    return save(scn, path)


def around(um, player, unit, x, y, size):
    """Units next to all four sides and the four corners of an object of size tiles at (x, y)."""
    d = size / 2 + 0.5
    for dx, dy in ((0, -d), (0, d), (-d, 0), (d, 0), (-d, -d), (d, -d), (-d, d), (d, d)):
        um.add_unit(player, unit, x=x + dx, y=y + dy)


def stress(path):
    scn = new_scenario(48)
    for t in scn.map_manager.terrain:
        if t.x < 16:
            t.elevation = min(4, t.x // 3)          # a slope from west to east
        if 34 <= t.x <= 39:
            t.terrain_id = TerrainId.WATER_DEEP if 35 <= t.x <= 38 else TerrainId.WATER_SHALLOW
    um = scn.unit_manager
    things = [(PlayerId.ONE, BuildingInfo.TOWN_CENTER.ID, 8, 8, 4), (PlayerId.ONE, BuildingInfo.HOUSE.ID, 22, 8, 2),
              (PlayerId.TWO, BuildingInfo.CASTLE.ID, 24, 22, 4), (PlayerId.TWO, BuildingInfo.BARRACKS.ID, 8, 24, 3),
              (PlayerId.GAIA, OtherInfo.TREE_OAK.ID, 14.5, 38.5, 1), (PlayerId.GAIA, OtherInfo.GOLD_MINE.ID, 20.5, 38.5, 1),
              (PlayerId.GAIA, OtherInfo.STONE_MINE.ID, 26.5, 38.5, 1),
              (PlayerId.GAIA, OtherInfo.CLIFF_DEFAULT_1.ID, 6, 40, 3), (PlayerId.GAIA, OtherInfo.MOUNTAIN_1.ID, 28, 32, 4)]
    for player, oid, x, y, size in things:
        um.add_unit(player, oid, x=x, y=y)
        around(um, PlayerId.ONE, UnitInfo.MAN_AT_ARMS.ID, x, y, size)
    for x, piece in ((33, BuildingInfo.BRIDGE_A_BOTTOM), (35, BuildingInfo.BRIDGE_A_MIDDLE),
                     (37, BuildingInfo.BRIDGE_A_MIDDLE), (39, BuildingInfo.BRIDGE_A_TOP)):
        um.add_unit(PlayerId.GAIA, piece.ID, x=x, y=24.5)
    for x in (34.5, 36.5, 38.5):
        um.add_unit(PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=x, y=24.5)
    return save(scn, path)


def set_civs(scn, n=8):
    scn.player_manager.active_players = n
    for i, civ in enumerate(CIVS[:n], 1):
        scn.player_manager.players[i].civilization = civ


def buildings_map(path, n_civs=8, step=7, per_row=40):
    names = [e for e in BuildingInfo]
    rows = -(-len(names) // per_row)
    scn = new_scenario(per_row * step + 8 if n_civs * rows < per_row else n_civs * rows * step + 8)
    set_civs(scn, n_civs)
    um = scn.unit_manager
    for p in range(n_civs):                     # one band of rows per player
        for i, e in enumerate(names):
            x, y = 4 + (i % per_row) * step, 4 + (p * rows + i // per_row) * step
            um.add_unit(PlayerId(p + 1), e.ID, x=x + 0.5, y=y + 0.5)
    return save(scn, path)


def units_map(path, step=3, per_row=30):
    ships, land = [], []
    for e in UnitInfo:
        (ships if units.is_boat(units.classify(e.name)) else land).append(e)
    rows_land, rows_ship = -(-len(land) // per_row), -(-len(ships) // per_row)
    water_y = 4 + rows_land * step + 2
    size = max(per_row * step + 8, water_y + rows_ship * step + 6)
    scn = new_scenario(size)
    for t in scn.map_manager.terrain:
        if t.y >= water_y - 1:
            t.terrain_id = TerrainId.WATER_DEEP
    um = scn.unit_manager
    for i, e in enumerate(land):
        um.add_unit(PlayerId.ONE, e.ID, x=4.5 + (i % per_row) * step, y=4.5 + (i // per_row) * step)
    for i, e in enumerate(ships):
        um.add_unit(PlayerId.TWO, e.ID, x=4.5 + (i % per_row) * step, y=water_y + 1.5 + (i // per_row) * step)
    return save(scn, path)


def village(path):
    scn = new_scenario(32)
    for t in scn.map_manager.terrain:
        if t.x >= 26:
            t.terrain_id = TerrainId.WATER_DEEP if t.x >= 28 else TerrainId.WATER_SHALLOW
        elif t.x >= 24:
            t.terrain_id = TerrainId.BEACH
        elif t.y < 6:
            t.terrain_id = TerrainId.FOREST_OAK
        elif t.y > 26:
            t.terrain_id = TerrainId.SNOW
        elif 10 <= t.x <= 14 and t.y == 16:
            t.terrain_id = TerrainId.ROAD
        elif t.x < 5:
            t.terrain_id = TerrainId.DIRT_1
        if 3 <= t.x <= 8 and 18 <= t.y <= 24:
            t.elevation = 3 if 4 <= t.x <= 7 and 19 <= t.y <= 23 else 1
    um = scn.unit_manager
    for x, y, oid in ((16, 16, BuildingInfo.TOWN_CENTER), (10, 11, BuildingInfo.HOUSE), (13, 11, BuildingInfo.HOUSE),
                      (20.5, 11.5, BuildingInfo.MILL), (20.5, 21.5, BuildingInfo.FARM), (11.5, 21.5, BuildingInfo.BLACKSMITH),
                      (25.5, 16.5, BuildingInfo.DOCK)):
        um.add_unit(PlayerId.ONE, oid.ID, x=x, y=y)
    for x in range(2, 24, 3):
        um.add_unit(PlayerId.GAIA, OtherInfo.TREE_OAK.ID, x=x + 0.5, y=2.5)
    um.add_unit(PlayerId.GAIA, OtherInfo.GOLD_MINE.ID, x=5.5, y=21.5)
    for x, y, uid in ((15.5, 19.5, UnitInfo.VILLAGER_MALE), (17.5, 19.5, UnitInfo.VILLAGER_FEMALE),
                      (20.5, 18.5, UnitInfo.VILLAGER_FEMALE_FARMER), (8.5, 14.5, UnitInfo.SHEEP),
                      (9.5, 14.5, UnitInfo.SHEEP), (12.5, 14.5, UnitInfo.SCOUT_CAVALRY)):
        um.add_unit(PlayerId.ONE if "SHEEP" not in uid.name else PlayerId.GAIA, uid.ID, x=x, y=y)
    um.add_unit(PlayerId.ONE, UnitInfo.FISHING_SHIP.ID, x=29.5, y=12.5)
    um.add_unit(PlayerId.GAIA, OtherInfo.FISH_TUNA.ID, x=29.5, y=20.5)
    return save(scn, path)


def facing(path):
    """8 knights in a circle: knight k has the rotation k*pi/4 and stands in the direction of that rotation from the
    center (angle from +x to +y). If the converter is correct, each knight faces away from the center in both games.
    8 archers in a row (west to east) with the same rotations. A flag at the north edge (tile y = 3)."""
    scn = new_scenario(32)
    um = scn.unit_manager
    for k in range(8):
        r = k * math.pi / 4
        um.add_unit(PlayerId.ONE, UnitInfo.KNIGHT.ID, x=16.5 + 6 * math.cos(r), y=16.5 + 6 * math.sin(r), rotation=r)
        um.add_unit(PlayerId.TWO, UnitInfo.ARCHER.ID, x=5.5 + 3 * k, y=27.5, rotation=r)
    um.add_unit(PlayerId.GAIA, OtherInfo.FLAG_A.ID, x=16.5, y=3.5)
    return save(scn, path)


def river(path):
    """Highland at elevation 2 with a river along tile x (deep in the middle), and a sea at elevation 0 in the south."""
    scn = new_scenario(32)
    for t in scn.map_manager.terrain:
        if t.y >= 28:
            t.terrain_id = TerrainId.WATER_DEEP                   # the sea at elevation 0
        elif t.y >= 24:
            t.elevation = 2 - (t.y - 24) // 2                     # a slope down to the sea
        else:
            t.elevation = 2
            if 10 <= t.y <= 15:
                t.terrain_id = TerrainId.WATER_DEEP if 12 <= t.y <= 13 else TerrainId.WATER_SHALLOW
    um = scn.unit_manager
    um.add_unit(PlayerId.ONE, BuildingInfo.TOWN_CENTER.ID, x=16, y=20)
    um.add_unit(PlayerId.ONE, BuildingInfo.DOCK.ID, x=6.5, y=10.5)
    for y, piece in ((10, BuildingInfo.BRIDGE_B_BOTTOM), (12, BuildingInfo.BRIDGE_B_MIDDLE),
                     (14, BuildingInfo.BRIDGE_B_TOP)):
        um.add_unit(PlayerId.GAIA, piece.ID, x=24.5, y=y + 1)
    um.add_unit(PlayerId.ONE, UnitInfo.FISHING_SHIP.ID, x=14.5, y=12.5)
    um.add_unit(PlayerId.ONE, UnitInfo.TRANSPORT_SHIP.ID, x=16.5, y=29.5)
    um.add_unit(PlayerId.GAIA, OtherInfo.FISH_TUNA.ID, x=10.5, y=13.5)
    um.add_unit(PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=16.5, y=17.5)
    return save(scn, path)


MAKERS = {"tiny": tiny, "stress": stress, "buildings": buildings_map, "units": units_map, "village": village,
          "facing": facing, "river": river}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=["gallery", *MAKERS])
    ap.add_argument("output")
    ap.add_argument("--kinds", default="BOU", help="gallery: B, O and/or U (default BOU)")
    a = ap.parse_args()
    if a.kind == "gallery":
        gallery(a.output, a.kinds)
    else:
        MAKERS[a.kind](a.output)
    print("Wrote", a.output)


if __name__ == "__main__":
    main()
