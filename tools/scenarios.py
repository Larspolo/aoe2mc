#!/usr/bin/env python3
"""
Make synthetic AoE2 DE scenarios for tests (no real map files necessary).

Usage:
    python tools/scenarios.py tiny OUT.aoe2scenario
    python tools/scenarios.py gallery OUT.aoe2scenario [--kinds BOU]
    python tools/scenarios.py moods OUT.aoe2scenario [--mood NIGHT]
    python tools/scenarios.py stress|buildings|units|village|facing|walls|river|river_town|four_civs|battle|large|owner_loop OUT.aoe2scenario

tiny:      24x24 tiles with land, shallow and deep water, a hill, buildings, units, a tree, a mine and fish.
gallery:   every object type of the parser in a grid (B = buildings, O = other objects, U = units).
stress:    units against every side of buildings, trees, mines, cliffs and a mountain; on slopes and on a bridge.
buildings: every building type for 8 civilizations with different architecture sets (players 1-8).
units:     every land unit on land and every ship on water.
village:   a small map with terrain types, water, a hill, a town and animals.
moods:     the village with a map color mood (--mood: DEFAULT, NIGHT, EVENING, SWAMP, MISTY ...), for a check of the
           moods in the game (#1598).
river:     a river at elevation 2 between land at elevation 2, with a dock, a bridge, a ship and fish (#165).
facing:    units at the rotations 0, pi/4 ... 7pi/4, to compare the facing in AoE2 and in Minecraft (docs/facing.md).
river_town: a 64x64 example map (examples/river_town.aoe2scenario): a walled town, a river with a bridge and a dock,
           a castle on a hill, forests, mines and animals (#204).
four_civs: an 80x80 example map (examples/four_civs.aoe2scenario): four towns of four architecture sets around a lake,
           each with its wonder (#205).
battle:    a 64x64 example map (examples/battle.aoe2scenario): two armies in formation, siege and a castle (#206).
large:     a 480x480 map with hills, lakes, forests, mines and 8 players with a town, to measure the time and memory of
           a conversion (tools/measure_convert.py, #690).
owner_loop: a 48x48 play-test map for one owner session (`human` skill, #1674): a town, a barracks, a lake with a
           dock, a transport ship and 3 militia; the bot (player 2) with 5 militia toward the town center.
walls:     palisade, stone and fortified walls with a gate and a corner, for 3 architecture sets (players 1, 4, 7).
"""
import argparse
import contextlib
import io
import math
import os
import shutil
import sys
import tempfile

import numpy as np

from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.object_support import Civilization
from AoE2ScenarioParser.datasets.other import OtherInfo
from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.datasets.terrains import TerrainId
from AoE2ScenarioParser.datasets.trigger_lists import ColorMood
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


def save(scn, path, name=None):
    """name: the file name in the file. The parser writes the name of path, so the bytes depend on it."""
    with contextlib.redirect_stdout(io.StringIO()), tempfile.TemporaryDirectory() as tmp:
        scn.write_to_file(os.path.join(tmp, name) if name else path)
        if name:
            shutil.move(os.path.join(tmp, name), path)
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


def triggers(path):
    """The tiny map with the common triggers of epic #645: timer messages, a unit in an area that creates an object,
    and a timer that removes an object (input of tools/triggers.py)."""
    with contextlib.redirect_stdout(io.StringIO()), tempfile.TemporaryDirectory() as tmp:   # the parser does not
        scn = AoE2DEScenario.from_file(tiny(os.path.join(tmp, "tiny.aoe2scenario")))     # overwrite its source
    tm = scn.trigger_manager
    t = tm.add_trigger("Welcome")
    t.new_condition.timer(timer=5)
    t.new_effect.send_chat(source_player=PlayerId.ONE, message="Welcome to the tiny map.")
    t.new_effect.display_instructions(source_player=PlayerId.ONE, message="Bring the knight to the hill.",
                                      display_time=10, instruction_panel_position=0)
    t = tm.add_trigger("Knight on the hill")
    t.new_condition.objects_in_area(quantity=1, source_player=PlayerId.ONE, object_list=UnitInfo.KNIGHT.ID,
                                    area_x1=3, area_y1=3, area_x2=6, area_y2=6)
    t.new_effect.create_object(source_player=PlayerId.ONE, object_list_unit_id=BuildingInfo.MONASTERY.ID,
                               location_x=8, location_y=4)
    t.new_effect.send_chat(source_player=PlayerId.ONE, message="A monastery stands now next to the hill.")
    t = tm.add_trigger("Archer leaves")
    t.new_condition.timer(timer=60)
    t.new_effect.remove_object(source_player=PlayerId.TWO, object_list_unit_id=UnitInfo.ARCHER.ID,
                               area_x1=0, area_y1=0, area_x2=23, area_y2=23)
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


def village(path, mood=None):
    """mood: the name of a map color mood (ColorMood), or None for the default."""
    scn = new_scenario(32)
    if mood:
        scn.map_manager.map_color_mood = ColorMood[mood.upper()]
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


def moods(path, mood="NIGHT"):
    """The village with the map color mood mood, for a check of the moods in the game (#1598, epic #1593)."""
    return village(path, mood)


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


def walls(path):
    """Per player (western, middle_eastern, east_asian) and per kind: a wall line along tile x with a gate in the
    middle, a corner and a line along tile y with a gate. The lines start at x = 2 and y = 2 + 10 * row."""
    scn = new_scenario(64)
    set_civs(scn)
    um = scn.unit_manager
    kinds = [("PALISADE_WALL", BuildingInfo.PALISADE_GATE_NORTHWEST_TO_SOUTHEAST),
             ("STONE_WALL", BuildingInfo.GATE_NORTHWEST_TO_SOUTHEAST),
             ("FORTIFIED_WALL", BuildingInfo.FORTIFIED_GATE_NORTHWEST_TO_SOUTHEAST)]
    row = 0
    for player in (PlayerId.ONE, PlayerId.FOUR, PlayerId.SEVEN):
        for x0, (wall, gate) in zip((2, 22, 42), kinds):
            y0 = 2 + 20 * row
            for x in [*range(x0, x0 + 4), *range(x0 + 8, x0 + 12)]:
                um.add_unit(player, BuildingInfo[wall].ID, x=x + 0.5, y=y0 + 0.5)
            um.add_unit(player, gate.ID, x=x0 + 6.0, y=y0 + 0.5)
            for y in [*range(y0 + 1, y0 + 5), *range(y0 + 9, y0 + 13)]:
                um.add_unit(player, BuildingInfo[wall].ID, x=x0 + 11.5, y=y + 0.5)
            um.add_unit(player, gate.ID, x=x0 + 11.5, y=y0 + 7.0)
        row += 1
    return save(scn, path)


def river(path):
    """Highland at elevation 2 with a river along tile x (deep in the middle), and a sea at elevation 0 in the south.
    A bridge and a Persian wall with a gate cross the river."""
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
    set_civs(scn, 4)                                                       # player 4: Persians (#192)
    for y in [*range(6, 11), *range(15, 20)]:                              # a wall with a gate across the river
        um.add_unit(PlayerId.FOUR, BuildingInfo.STONE_WALL.ID, x=12.5, y=y + 0.5)
    um.add_unit(PlayerId.FOUR, BuildingInfo.GATE_NORTHWEST_TO_SOUTHEAST.ID, x=12.5, y=13.0)
    for y, piece in ((10, BuildingInfo.BRIDGE_B_BOTTOM), (12, BuildingInfo.BRIDGE_B_MIDDLE),
                     (14, BuildingInfo.BRIDGE_B_TOP)):
        um.add_unit(PlayerId.GAIA, piece.ID, x=24.5, y=y + 1)
    um.add_unit(PlayerId.ONE, UnitInfo.FISHING_SHIP.ID, x=14.5, y=12.5)
    um.add_unit(PlayerId.ONE, UnitInfo.TRANSPORT_SHIP.ID, x=16.5, y=29.5)
    um.add_unit(PlayerId.GAIA, OtherInfo.FISH_TUNA.ID, x=10.5, y=13.5)
    um.add_unit(PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=16.5, y=17.5)
    return save(scn, path)


def river_town(path):
    """Example map: a town at elevation 1 north of a river at elevation 0, a castle on a hill at elevation 3 in the
    south-east and a forest in the south-west. No randomness: the file is the same on each run."""
    scn = new_scenario(64)
    set_civs(scn, 1)                                                     # player 1: Britons (western)
    for t in scn.map_manager.terrain:
        x, y, hill = t.x, t.y, max(abs(t.x - 48), abs(t.y - 50))
        if 30 <= y <= 35:                                                # the river along tile x
            t.terrain_id = TerrainId.WATER_DEEP if 32 <= y <= 33 else TerrainId.WATER_SHALLOW
        elif y in (29, 36):
            t.terrain_id = TerrainId.BEACH
        elif 20 <= x <= 21 and (y >= 26 or 37 <= y <= 42):              # the road to the bridge
            t.terrain_id = TerrainId.ROAD
        elif y <= 4 or (x <= 16 and y >= 42):
            t.terrain_id = TerrainId.FOREST_OAK
        elif hill <= 5:
            t.terrain_id = TerrainId.GRASS_2
        if y <= 4:
            t.elevation = 2
        elif y <= 25:
            t.elevation = 1
        elif y >= 40:
            t.elevation = 3 if hill <= 4 else 2 if hill <= 5 else 1
    um = scn.unit_manager
    for x, y in ((x, y) for x in range(64) for y in [*range(5), *range(42, 64)]
                 if (y <= 4 or x <= 16) and (x * 7 + y * 3) % 5 and not (14 <= x <= 16 and y < 44)):
        um.add_unit(PlayerId.GAIA, OtherInfo.TREE_OAK.ID, x=x + 0.5, y=y + 0.5)
    for y in [*range(8, 15), *range(19, 26)]:                            # the west wall with a gate
        um.add_unit(PlayerId.ONE, BuildingInfo.STONE_WALL.ID, x=5.5, y=y + 0.5)
    um.add_unit(PlayerId.ONE, BuildingInfo.GATE_NORTHWEST_TO_SOUTHEAST.ID, x=5.5, y=17.0)
    for x in [*range(5, 22), *range(26, 45)]:                            # the north wall with a gate
        um.add_unit(PlayerId.ONE, BuildingInfo.STONE_WALL.ID, x=x + 0.5, y=7.5)
    um.add_unit(PlayerId.ONE, BuildingInfo.GATE_NORTHWEST_TO_SOUTHEAST.ID, x=24.0, y=7.5)
    for x, y, b in ((24, 17, BuildingInfo.TOWN_CENTER), (38, 17, BuildingInfo.MARKET), (12, 12, BuildingInfo.MILL),
                    (16, 10, BuildingInfo.HOUSE), (19, 10, BuildingInfo.HOUSE), (30, 10, BuildingInfo.HOUSE),
                    (33, 10, BuildingInfo.HOUSE), (30, 23, BuildingInfo.HOUSE), (33, 23, BuildingInfo.HOUSE),
                    (8.5, 12.5, BuildingInfo.FARM), (8.5, 21.5, BuildingInfo.FARM), (11.5, 21.5, BuildingInfo.FARM),
                    (14.5, 21.5, BuildingInfo.FARM), (16.5, 15.5, BuildingInfo.BLACKSMITH),
                    (40.5, 11.5, BuildingInfo.BARRACKS), (40.5, 30.5, BuildingInfo.DOCK),
                    (48, 50, BuildingInfo.CASTLE), (23.5, 38.5, BuildingInfo.WATCH_TOWER),
                    (18, 44, BuildingInfo.LUMBER_CAMP), (34, 50, BuildingInfo.MINING_CAMP)):
        um.add_unit(PlayerId.ONE, b.ID, x=x, y=y)
    for y, piece in ((30, BuildingInfo.BRIDGE_A_BOTTOM), (32, BuildingInfo.BRIDGE_A_MIDDLE),
                     (34, BuildingInfo.BRIDGE_A_TOP)):
        um.add_unit(PlayerId.GAIA, piece.ID, x=20.5, y=y + 1)
    for x, y, o in ((30.5, 46.5, OtherInfo.GOLD_MINE), (31.5, 46.5, OtherInfo.GOLD_MINE),
                    (30.5, 47.5, OtherInfo.GOLD_MINE), (34.5, 57.5, OtherInfo.STONE_MINE),
                    (35.5, 57.5, OtherInfo.STONE_MINE), (28.5, 20.5, OtherInfo.FORAGE_BUSH),
                    (28.5, 21.5, OtherInfo.FORAGE_BUSH), (50.5, 33.5, OtherInfo.FISH_PERCH),
                    (12.5, 32.5, OtherInfo.FISH_PERCH), (58.5, 30.5, OtherInfo.SHORE_FISH)):
        um.add_unit(PlayerId.GAIA, o.ID, x=x, y=y)
    for x, y, u in ((22.5, 21.5, UnitInfo.VILLAGER_MALE), (26.5, 21.5, UnitInfo.VILLAGER_FEMALE),
                    (8.5, 21.5, UnitInfo.VILLAGER_FEMALE_FARMER), (14.5, 21.5, UnitInfo.VILLAGER_MALE_FARMER),
                    (29.5, 47.5, UnitInfo.VILLAGER_MALE_GOLD_MINER), (19.5, 44.5, UnitInfo.VILLAGER_MALE_LUMBERJACK),
                    (36.5, 20.5, UnitInfo.TRADE_CART_FULL), (42.5, 15.5, UnitInfo.MAN_AT_ARMS),
                    (43.5, 15.5, UnitInfo.MAN_AT_ARMS), (24.5, 9.5, UnitInfo.SPEARMAN),
                    (46.5, 45.5, UnitInfo.KNIGHT), (49.5, 45.5, UnitInfo.KNIGHT), (52.5, 49.5, UnitInfo.LONGBOWMAN),
                    (44.5, 32.5, UnitInfo.FISHING_SHIP), (56.5, 33.5, UnitInfo.WAR_GALLEY),
                    (8.5, 33.5, UnitInfo.TRANSPORT_SHIP)):
        um.add_unit(PlayerId.ONE, u.ID, x=x, y=y)
    for x, y, u in ((28.5, 13.5, UnitInfo.SHEEP), (29.5, 14.5, UnitInfo.SHEEP), (27.5, 14.5, UnitInfo.SHEEP),
                    (22.5, 50.5, UnitInfo.DEER), (23.5, 52.5, UnitInfo.DEER), (21.5, 53.5, UnitInfo.DEER),
                    (26.5, 59.5, UnitInfo.WILD_BOAR), (40.5, 40.5, UnitInfo.TURKEY), (58.5, 22.5, UnitInfo.COW_A)):
        um.add_unit(PlayerId.GAIA, u.ID, x=x, y=y)
    return save(scn, path, "river_town.aoe2scenario")


def four_civs(path):
    """Example map: four towns around a lake, one per quarter, with mirrored layouts. Player p has the civilization,
    ground, forest, trees and unique unit of FOUR_CIVS[p - 1]. No randomness: the file is the same on each run."""
    scn = new_scenario(80)
    scn.player_manager.active_players = 4
    for p, (civ, *_) in enumerate(FOUR_CIVS, 1):
        scn.player_manager.players[p].civilization = civ
        sx, sy = (1 if (p - 1) & 1 else -1), (1 if (p - 1) & 2 else -1)   # the quarter: NW, NE, SW, SE
        view = scn.player_manager.players[p]                              # 5 tiles in front of the town center
        view.initial_player_view_x, view.initial_player_view_y = 40 + sx * 18, 40 + sy * 18
    quarter = lambda x, y: (x >= 40) + 2 * (y >= 40)                    # noqa: E731 - 0 NW, 1 NE, 2 SW, 3 SE
    for t in scn.map_manager.terrain:
        r, edge = math.hypot(t.x - 39.5, t.y - 39.5), min(t.x, t.y, 79 - t.x, 79 - t.y)
        _, ground, forest, *_ = FOUR_CIVS[quarter(t.x, t.y)]
        t.terrain_id = (TerrainId.WATER_DEEP if r <= 8 else TerrainId.WATER_SHALLOW if r <= 12 else
                        TerrainId.BEACH if r <= 13.5 else forest if edge <= 3 else ground)
        if r > 16:
            t.elevation = 1
    um = scn.unit_manager
    for x, y in ((x, y) for x in range(80) for y in range(80)
                 if min(x, y, 79 - x, 79 - y) <= 3 and (x * 7 + y * 3) % 5):
        um.add_unit(PlayerId.GAIA, FOUR_CIVS[quarter(x, y)][3].ID, x=x + 0.5, y=y + 0.5)
    for (sx, sy), (*_, unique), player in zip(((-1, -1), (1, -1), (-1, 1), (1, 1)), FOUR_CIVS, PlayerId.all()[1:]):
        at = lambda d, e: dict(x=40 + sx * d, y=40 + sy * e)            # noqa: E731 - offsets toward the lake
        for d, e, b in ((23, 23, BuildingInfo.TOWN_CENTER), (12.5, 12.5, BuildingInfo.WONDER),
                        (8.5, 8.5, BuildingInfo.DOCK), (24, 14, BuildingInfo.MARKET),
                        (14.5, 24.5, BuildingInfo.BARRACKS), (31.5, 31.5, BuildingInfo.MONASTERY),
                        (30, 23, BuildingInfo.HOUSE), (30, 19, BuildingInfo.HOUSE), (23, 30, BuildingInfo.HOUSE),
                        (19, 30, BuildingInfo.HOUSE), (17.5, 17.5, BuildingInfo.WATCH_TOWER)):
            um.add_unit(player, b.ID, **at(d, e))
        for d, e, u in ((20.5, 20.5, UnitInfo.VILLAGER_MALE), (21.5, 18.5, UnitInfo.VILLAGER_FEMALE),
                        (18.5, 21.5, unique), (19.5, 22.5, unique), (11.5, 18.5, UnitInfo.MONK),
                        (6.5, 3.5, UnitInfo.FISHING_SHIP)):
            um.add_unit(player, u.ID, **at(d, e))
        um.add_unit(PlayerId.GAIA, OtherInfo.FISH_TUNA.ID, **at(3.5, 6.5))
        um.add_unit(PlayerId.GAIA, UnitInfo.SHEEP.ID, **at(26.5, 18.5))
    return save(scn, path, "four_civs.aoe2scenario")


# Per player of four_civs (NW, NE, SW, SE): civilization, ground, forest, tree, unique unit
FOUR_CIVS = [(Civilization.BRITONS, TerrainId.GRASS_1, TerrainId.FOREST_OAK, OtherInfo.TREE_OAK, UnitInfo.LONGBOWMAN),
             (Civilization.PERSIANS, TerrainId.DESERT_SAND, TerrainId.FOREST_PALM_DESERT, OtherInfo.TREE_PALM_FOREST,
              UnitInfo.WAR_ELEPHANT),
             (Civilization.JAPANESE, TerrainId.GRASS_3, TerrainId.FOREST_BAMBOO, OtherInfo.TREE_BAMBOO_FOREST,
              UnitInfo.SAMURAI),
             (Civilization.AZTECS, TerrainId.GRASS_JUNGLE, TerrainId.FOREST_JUNGLE, OtherInfo.TREE_JUNGLE,
              UnitInfo.JAGUAR_WARRIOR)]


MUD = ((19, 31, 8), (26, 34, 5), (33, 32, 12), (41, 30, 6), (46, 34, 9), (38, 36, 4), (12, 33, 3))   # x, y, r²


def battle(path):
    """Example map: two armies in formation face each other on an open field. Britons (player 1) in the north
    with a castle on a hill, Persians (player 2) in the south with a siege camp. No randomness."""
    scn = new_scenario(64)
    scn.player_manager.active_players = 2
    scn.player_manager.players[1].civilization = Civilization.BRITONS                  # western
    scn.player_manager.players[2].civilization = Civilization.PERSIANS                 # middle_eastern
    for t in scn.map_manager.terrain:
        x, y, hill = t.x, t.y, max(abs(t.x - 32), abs(t.y - 8))
        if x <= 3 or x >= 60:
            t.terrain_id = TerrainId.FOREST_OAK
        elif any((x - cx) ** 2 + 2 * (y - cy) ** 2 <= r for cx, cy, r in MUD):          # trampled ground
            t.terrain_id = TerrainId.DIRT_2
        elif y >= 50:
            t.terrain_id = TerrainId.DIRT_1
        t.elevation = 2 if hill <= 5 else 1 if hill <= 7 else 0
    um = scn.unit_manager
    for x, y in ((x, y) for x in [*range(4), *range(60, 64)] for y in range(64) if (x * 3 + y * 7) % 4):
        um.add_unit(PlayerId.GAIA, OtherInfo.TREE_OAK.ID, x=x + 0.5, y=y + 0.5)
    for x, y, b in ((32, 8, BuildingInfo.CASTLE), (20.5, 12.5, BuildingInfo.GUARD_TOWER),
                    (43.5, 12.5, BuildingInfo.GUARD_TOWER), (14, 5, BuildingInfo.BARRACKS),
                    (50, 5, BuildingInfo.ARCHERY_RANGE)):
        um.add_unit(PlayerId.ONE, b.ID, x=x, y=y)
    for x, y, b in ((22, 58, BuildingInfo.SIEGE_WORKSHOP), (42, 58, BuildingInfo.STABLE),
                    (32, 59, BuildingInfo.MONASTERY)):
        um.add_unit(PlayerId.TWO, b.ID, x=x, y=y)
    south, north = math.pi / 2, 3 * math.pi / 2                                       # rotation: angle from +x to +y
    armies = ((PlayerId.ONE, south, ((24.5, 1.5, ((12, UnitInfo.HALBERDIER),)), (23.0, 1.5, ((12, UnitInfo.CHAMPION),)),
                                     (21.5, 1.5, ((12, UnitInfo.LONGBOWMAN),)), (20.0, 1.5, ((12, UnitInfo.ARBALESTER),)),
                                     (17.0, 2.5, ((3, UnitInfo.MANGONEL), (2, UnitInfo.SCORPION), (3, UnitInfo.MANGONEL))))),
              (PlayerId.TWO, north, ((39.5, 1.5, ((12, UnitInfo.PIKEMAN),)), (41.0, 1.5, ((12, UnitInfo.TWO_HANDED_SWORDSMAN),)),
                                     (42.5, 1.5, ((12, UnitInfo.CROSSBOWMAN),)), (44.0, 1.5, ((12, UnitInfo.ELITE_SKIRMISHER),)),
                                     (48.0, 3.0, ((2, UnitInfo.BATTERING_RAM), (2, UnitInfo.SIEGE_TOWER), (2, UnitInfo.BATTERING_RAM))),
                                     (51.5, 3.0, ((2, UnitInfo.TREBUCHET), (2, UnitInfo.BOMBARD_CANNON), (2, UnitInfo.TREBUCHET))))))
    for player, rot, rows in armies:
        for y, step, groups in rows:                                                   # one row along tile x, centered
            line = [u for n, u in groups for _ in range(n)]
            for i, u in enumerate(line):
                um.add_unit(player, u.ID, x=32.5 + (i - (len(line) - 1) / 2) * step, y=y, rotation=rot)
    for player, rot, y, u in ((PlayerId.ONE, south, (22.0, 23.5), UnitInfo.CAVALIER),
                              (PlayerId.ONE, south, (19.0,), UnitInfo.LIGHT_CAVALRY),
                              (PlayerId.TWO, north, (40.0, 42.0), UnitInfo.WAR_ELEPHANT),
                              (PlayerId.TWO, north, (44.0,), UnitInfo.CAMEL_RIDER)):
        for yy in y:                                                                   # cavalry on both wings
            for x in (*range(8, 15, 2), *range(51, 58, 2)):
                um.add_unit(player, u.ID, x=x + 0.5, y=yy, rotation=rot)
    for player, rot, x, y, u in ((PlayerId.ONE, south, 32.5, 14.5, UnitInfo.KING),
                                 (PlayerId.ONE, south, 30.5, 15.5, UnitInfo.MONK),
                                 (PlayerId.ONE, south, 34.5, 15.5, UnitInfo.MONK),
                                 (PlayerId.TWO, north, 32.5, 55.5, UnitInfo.KING),
                                 (PlayerId.TWO, north, 30.5, 54.5, UnitInfo.MONK),
                                 (PlayerId.TWO, north, 34.5, 54.5, UnitInfo.MONK)):
        um.add_unit(player, u.ID, x=x, y=y, rotation=rot)
    for x, y, o in ((26.5, 32.5, OtherInfo.SKELETON), (37.5, 31.5, OtherInfo.CRATER), (30.5, 34.5, OtherInfo.FLAG_A)):
        um.add_unit(PlayerId.GAIA, o.ID, x=x, y=y)
    return save(scn, path, "battle.aoe2scenario")


def large(path, size=480, players=8):
    """A large map (#690): smooth hills (elevation 0-4), lakes, forests of trees, gold and stone mines, berries, and
    per player a town center, 4 houses and 30 units, as a real 8-player map has them. Seeded: the same bytes each run."""
    rng = np.random.default_rng(690)
    k = rng.uniform(0.01, 0.04, (4, 2)) * 480 / size   # a smaller map is a scaled copy (tests)
    def field(x, y):                                # a smooth noise of 4 waves, about -1 .. 1
        return sum(math.sin(a * x + 3 * i) * math.cos(b * y + i) for i, (a, b) in enumerate(k)) / 2
    scn = new_scenario(size)
    set_civs(scn, players)
    um, forest = scn.unit_manager, []
    for t in scn.map_manager.terrain:
        f = field(t.x, t.y)
        if f < -0.75:
            t.terrain_id = TerrainId.WATER_DEEP if f < -0.9 else TerrainId.WATER_SHALLOW
        elif f > 0.55:
            t.terrain_id, t.elevation = TerrainId.FOREST_OAK, 2
            forest.append((t.x, t.y))
        else:
            t.terrain_id = (TerrainId.GRASS_1, TerrainId.GRASS_2, TerrainId.DIRT_1)[(t.x // 24 + t.y // 24) % 3]
            t.elevation = int(max(0, f + 0.6) * 4)
    for x, y in forest:
        um.add_unit(PlayerId.GAIA, OtherInfo.TREE_OAK_FOREST.ID, x=x + 0.5, y=y + 0.5)
    for i in range(players):                        # the towns on a circle, as a real map places the players
        a = 2 * math.pi * i / players
        cx, cy = int(size / 2 + size * 0.38 * math.cos(a)), int(size / 2 + size * 0.38 * math.sin(a))
        for t in scn.map_manager.terrain:
            if abs(t.x - cx) < 14 and abs(t.y - cy) < 14:
                t.terrain_id, t.elevation = TerrainId.GRASS_1, 1
        p = PlayerId(i + 1)
        um.add_unit(p, BuildingInfo.TOWN_CENTER.ID, x=cx, y=cy)
        for dx, dy in ((-7, -7), (7, -7), (-7, 7), (7, 7)):
            um.add_unit(p, BuildingInfo.HOUSE.ID, x=cx + dx, y=cy + dy)
        for j in range(30):
            unit = UnitInfo.VILLAGER_MALE if j < 20 else UnitInfo.MILITIA
            um.add_unit(p, unit.ID, x=cx - 9.5 + j % 10 * 2, y=cy + 4.5 + j // 10 * 1.5)
        for oid, d in ((OtherInfo.GOLD_MINE.ID, (10, -11)), (OtherInfo.STONE_MINE.ID, (-11, 10)),
                       (OtherInfo.FORAGE_BUSH.ID, (11, 10))):
            for n in range(5):
                um.add_unit(PlayerId.GAIA, oid, x=cx + d[0] + n % 3 + 0.5, y=cy + d[1] + n // 3 + 0.5)
    return save(scn, path, "large.aoe2scenario")


def owner_loop(path):
    """A 48 x 48 play-test map for one owner session of the `human` skill (#1674): player 1 (Britons) in the north-west
    with a barracks, and a lake with a dock, a transport ship and 3 militia in the south-west corner; player 2 (Franks,
    the bot) in the south-east with 5 militia (bot.GROUP) on the diagonal toward the town center of player 1. The
    nearest units of player 1 to the bot are the villagers at the town center, so the first attack goes there (the
    arrows of #1204), not to the dock."""
    scn = new_scenario(48)
    scn.player_manager.active_players = 2
    scn.player_manager.players[1].civilization = Civilization.BRITONS
    scn.player_manager.players[2].civilization = Civilization.FRANKS
    for t in scn.map_manager.terrain:
        x, y = t.x, t.y
        d = max(abs(x - 6), abs(y - 40))                                 # the lake in the south-west corner
        if d <= 3:
            t.terrain_id = TerrainId.WATER_DEEP
        elif d <= 5:
            t.terrain_id = TerrainId.WATER_SHALLOW
        elif d == 6:
            t.terrain_id = TerrainId.BEACH
        elif y <= 1 or x >= 46 or (x <= 1 and y <= 20):
            t.terrain_id = TerrainId.FOREST_OAK
    um = scn.unit_manager
    for x in range(3, 22, 2):                                            # the wood lines of both players
        um.add_unit(PlayerId.GAIA, OtherInfo.TREE_OAK.ID, x=x + 0.5, y=3.5)
    for y in range(26, 45, 2):
        um.add_unit(PlayerId.GAIA, OtherInfo.TREE_OAK.ID, x=44.5, y=y + 0.5)
    for (cx, cy), p in (((12, 12), PlayerId.ONE), ((36, 36), PlayerId.TWO)):
        s = 1 if p == PlayerId.ONE else -1
        for dx, dy, b in ((0, 0, BuildingInfo.TOWN_CENTER), (-5, -4, BuildingInfo.HOUSE), (-2, -5, BuildingInfo.HOUSE)):
            um.add_unit(p, b.ID, x=cx + s * dx, y=cy + s * dy)
        for dx, dy, u in ((-1.5, 3.5, UnitInfo.VILLAGER_MALE), (0.5, 3.5, UnitInfo.VILLAGER_FEMALE),
                          (2.5, 3.5, UnitInfo.VILLAGER_MALE), (3.5, 1.5, UnitInfo.VILLAGER_FEMALE),
                          (3.5, -0.5, UnitInfo.VILLAGER_MALE), (3.5, -2.5, UnitInfo.VILLAGER_FEMALE)):
            um.add_unit(p, u.ID, x=cx + s * dx, y=cy + s * dy)
        for dx, dy, o in ((6.5, 4.5, OtherInfo.FORAGE_BUSH), (7.5, 4.5, OtherInfo.FORAGE_BUSH),
                          (6.5, 5.5, OtherInfo.FORAGE_BUSH), (7.5, 5.5, OtherInfo.FORAGE_BUSH),
                          (8.5, -3.5, OtherInfo.GOLD_MINE), (9.5, -3.5, OtherInfo.GOLD_MINE),
                          (8.5, -2.5, OtherInfo.GOLD_MINE), (-6.5, 2.5, OtherInfo.STONE_MINE),
                          (-6.5, 3.5, OtherInfo.STONE_MINE)):
            um.add_unit(PlayerId.GAIA, o.ID, x=cx + s * dx, y=cy + s * dy)
        for dx, dy in ((-3.5, 5.5), (-2.5, 6.5), (-1.5, 5.5), (-3.5, 6.5)):
            um.add_unit(PlayerId.GAIA, UnitInfo.SHEEP.ID, x=cx + s * dx, y=cy + s * dy)
    um.add_unit(PlayerId.ONE, BuildingInfo.BARRACKS.ID, x=19.5, y=12.5)         # a building to repair (#1332)
    um.add_unit(PlayerId.ONE, BuildingInfo.DOCK.ID, x=6.5, y=33.5)              # on the north beach of the lake
    um.add_unit(PlayerId.ONE, UnitInfo.TRANSPORT_SHIP.ID, x=6.5, y=37.5)
    for x in (2.5, 3.5, 4.5):                                                    # 3 militia for the ship (#1492)
        um.add_unit(PlayerId.ONE, UnitInfo.MILITIA.ID, x=x, y=31.5)
    for k in range(5):                                                           # the first wave of the bot
        um.add_unit(PlayerId.TWO, UnitInfo.MILITIA.ID, x=26.5 + k, y=30.5 - k)
    return save(scn, path, "owner_loop.aoe2scenario")


MAKERS = {"tiny": tiny, "stress": stress, "buildings": buildings_map, "units": units_map, "village": village, "facing": facing,
          "walls": walls, "river": river, "river_town": river_town, "four_civs": four_civs, "battle": battle,
          "triggers": triggers, "large": large,
          "moods": moods,
          "owner_loop": owner_loop}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=["gallery", *MAKERS])
    ap.add_argument("output")
    ap.add_argument("--kinds", default="BOU", help="gallery: B, O and/or U (default BOU)")
    ap.add_argument("--mood", default="NIGHT", choices=[m.name for m in ColorMood], type=str.upper,
                    help="moods: the map color mood (default NIGHT)")
    a = ap.parse_args()
    if a.kind == "gallery":
        gallery(a.output, a.kinds)
    elif a.kind == "moods":
        moods(a.output, a.mood)
    else:
        MAKERS[a.kind](a.output)
    print("Wrote", a.output)


if __name__ == "__main__":
    main()
