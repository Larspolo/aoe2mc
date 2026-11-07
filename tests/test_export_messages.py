"""game/export.py: the scenario texts of aoe2mc.json "messages" go to the message manager (#6028)."""
import contextlib
import io
import json
import os
import shutil

import export  # noqa: E402
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario  # noqa: E402

TEXTS = {"instructions": "Build a wall.", "hints": "Mine the gold first.", "victory": "You won.",
         "loss": "You lost.", "history": "Long ago.", "scouts": "Scout the north.", "objectives": "Not a field."}


def read(path):
    with contextlib.redirect_stdout(io.StringIO()):
        return AoE2DEScenario.from_file(str(path))


def world_copy(tiny_world, tmp_path):
    world = str(tmp_path / "world")
    shutil.copytree(tiny_world[0], world)
    return world


def test_messages_are_exported_and_read_back(tiny_world, tmp_path):
    world = world_copy(tiny_world, tmp_path)
    path = os.path.join(world, "aoe2mc.json")
    with open(path) as f:
        data = json.load(f)
    data["messages"] = TEXTS
    with open(path, "w") as f:
        json.dump(data, f)
    scn = read(export.export(world, str(tmp_path / "out.aoe2scenario")))
    fields = [k for k in TEXTS if k != "objectives"]           # objectives: from the triggers, no field
    assert {k: getattr(scn.message_manager, k) for k in fields} == {k: TEXTS[k] for k in fields}


def test_world_without_messages_exports_as_before(tiny_world, tmp_path):
    world = world_copy(tiny_world, tmp_path)
    path = os.path.join(world, "aoe2mc.json")
    with open(path) as f:
        data = json.load(f)
    data.pop("messages", None)
    with open(path, "w") as f:
        json.dump(data, f)
    scn = read(export.export(world, str(tmp_path / "plain.aoe2scenario")))
    assert not scn.message_manager.instructions
    assert not scn.message_manager.victory
