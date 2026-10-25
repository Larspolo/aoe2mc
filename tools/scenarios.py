#!/usr/bin/env python3
"""
Make synthetic AoE2 DE scenarios for tests (no real map files necessary).

Usage:
    python tools/scenarios.py tiny OUT.aoe2scenario
    python tools/scenarios.py gallery OUT.aoe2scenario [--kinds BOU]

tiny:    24x24 tiles with land, shallow and deep water, a hill, buildings, units, a tree, a mine and fish.
gallery: every object type of the parser in a grid (B = buildings, O = other objects, U = units).
"""
import argparse
import contextlib
import io

from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.other import OtherInfo
from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.datasets.terrains import TerrainId
from AoE2ScenarioParser.datasets.units import UnitInfo
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario


def new_scenario(size):
    with contextlib.redirect_stdout(io.StringIO()):     # the parser prints a lot of status text
        scn = AoE2DEScenario.from_default()
    scn.map_manager.map_size = size
    return scn


def save(scn, path):
    with contextlib.redirect_stdout(io.StringIO()):
        scn.write_to_file(path)
    return path


def tiny(path):
    scn = new_scenario(24)
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=["tiny", "gallery"])
    ap.add_argument("output")
    ap.add_argument("--kinds", default="BOU", help="gallery: B, O and/or U (default BOU)")
    a = ap.parse_args()
    if a.kind == "tiny":
        tiny(a.output)
    else:
        gallery(a.output, a.kinds)
    print("Wrote", a.output)


if __name__ == "__main__":
    main()
