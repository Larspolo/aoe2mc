"""game/export.py: a played world back to an .aoe2scenario (#4198)."""
import contextlib
import io
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import export  # noqa: E402
import savegame  # noqa: E402
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario  # noqa: E402


def read(path):
    with contextlib.redirect_stdout(io.StringIO()):
        return AoE2DEScenario.from_file(str(path))


def units(scn):
    return [(u.unit_const, int(u.player), u.x, u.y) for p in scn.unit_manager.units for u in p]


def test_world_gives_its_map_players_and_objects(tiny_world, tmp_path):
    world = tiny_world[0]
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    scn = read(export.export(world, str(tmp_path / "back.aoe2scenario")))
    assert scn.map_manager.map_size == data["map_size"]
    terrain = [[int(v) for v in r.split()] for r in data["terrain"]]
    elevation = [[int(v) for v in r.split()] for r in data["elevation"]]
    assert all(t.terrain_id == terrain[t.y][t.x] and t.elevation == elevation[t.y][t.x] for t in scn.map_manager.terrain)
    assert sorted((u[0], u[1]) for u in units(scn)) == sorted((o["id"], o["player"]) for o in data["objects"])


def test_save_gives_the_end_of_the_game(tiny_world, tmp_path):
    world = tiny_world[0]
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    T = data["tile_size"]
    by = {o["name"]: o for o in data["objects"]}
    knight, villager, archer, gold = by["KNIGHT"], by["VILLAGER_MALE"], by["ARCHER"], by["GOLD_MINE"]
    save = tmp_path / "save"
    shutil.copytree(world, save / "world")
    house = [4 * T, 5 * T, 8 * T, 9 * T]                               # x0, x1, z0, z1: a new house at tile (4.5, 8.5)
    gold_tile = savegame.pack({(int(gold["tile"][0]), int(gold["tile"][1])): 0})
    state = {"players": {
        "1": {"soldiers": {}, "villagers": {villager["uuid"]: {}},     # the knight died
              "sites": savegame.pack([{"name": "HOUSE", "player": 1, "footprint": tuple(house), "progress": 1.0}]),
              "map": {"mines": {"gold": gold_tile}}},
        "2": {"soldiers": {archer["uuid"]: "ARCHER"}, "villagers": {}}}}
    with open(save / savegame.FILE, "w") as f:
        json.dump(state, f)
    got = units(read(export.export(str(save), str(tmp_path / "end.aoe2scenario"))))
    ids = [(u[0], u[1]) for u in got]
    assert (knight["id"], 1) not in ids
    assert (villager["id"], 1) in ids and (archer["id"], 2) in ids
    assert gold["id"] not in [u[0] for u in got]
    assert (by["HOUSE"]["id"], 1, 4.5, 8.5) in got
