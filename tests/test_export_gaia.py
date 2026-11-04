"""game/export.py: cut trees, empty food sources and hunted animals are not exported (#5672)."""
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


def gaia_world(tiny_world):
    world = tiny_world[0]
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    by = {o["name"]: o for o in data["objects"]}
    tree, fish, sheep = by["TREE_OAK"], by["FISH_TUNA"], by["SHEEP"]
    return world, by, tree, fish, sheep


def test_save_drops_the_cut_tree_the_empty_fish_and_the_hunted_sheep(tiny_world, tmp_path, monkeypatch):
    world, by, tree, fish, sheep = gaia_world(tiny_world)
    tree_tile = (int(tree["tile"][0]), int(tree["tile"][1]))
    fish_tile = (int(fish["tile"][0]), int(fish["tile"][1]))
    save = tmp_path / "save"
    shutil.copytree(world, save / "world")
    with open(os.path.join(world, "aoe2mc.json")) as f:
        objects = json.load(f)["objects"]
    alive = {"1": {}, "2": {}}                                         # the units of the players live at the end
    for o in objects:
        if o["kind"] == "unit" and o["player"] and o.get("uuid"):
            alive[str(o["player"])][o["uuid"]] = {}
    state = {"players": {
        "1": {"soldiers": {}, "villagers": alive["1"],
              "map": {"trees": savegame.pack({tree_tile: 0}), "fish": savegame.pack({fish_tile: 0})}},
        "2": {"soldiers": alive["2"], "villagers": {}}}}
    with open(save / savegame.FILE, "w") as f:
        json.dump(state, f)
    positions = export.positions
    monkeypatch.setattr(export, "positions", lambda w: {u: p for u, p in positions(w).items() if u != sheep["uuid"]})
    got = units(read(export.export(str(save), str(tmp_path / "end.aoe2scenario"))))
    ids = [u[0] for u in got]
    assert tree["id"] not in ids and fish["id"] not in ids and sheep["id"] not in ids
    assert len(got) == len(json.load(open(os.path.join(world, "aoe2mc.json")))["objects"]) - 3


def test_world_without_save_keeps_the_tree_the_fish_and_the_sheep(tiny_world, tmp_path):
    world, by, tree, fish, sheep = gaia_world(tiny_world)
    got = units(read(export.export(world, str(tmp_path / "back.aoe2scenario"))))
    ids = [(u[0], u[1]) for u in got]
    assert (tree["id"], tree["player"]) in ids
    assert (fish["id"], fish["player"]) in ids
    assert (sheep["id"], sheep["player"]) in ids
