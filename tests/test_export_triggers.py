"""game/export.py: the export keeps the triggers and variables of a converted scenario (#6031)."""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import export  # noqa: E402
import pytest  # noqa: E402
import savegame  # noqa: E402
import scenarios  # noqa: E402
from AoE2ScenarioParser.datasets.players import PlayerId  # noqa: E402
from AoE2ScenarioParser.datasets.units import UnitInfo  # noqa: E402
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario  # noqa: E402

import aoe2mc  # noqa: E402


def read(path):
    with contextlib.redirect_stdout(io.StringIO()):
        return AoE2DEScenario.from_file(str(path))


def with_triggers(path):
    """The tiny map with a variable and a trigger: "Destroy Object" on the archer, then a chat message."""
    with tempfile.TemporaryDirectory() as tmp:
        scn = read(scenarios.tiny(os.path.join(tmp, "tiny.aoe2scenario")))
    archer = next(u for u in scn.unit_manager.units[2] if u.unit_const == UnitInfo.ARCHER.ID)
    scn.trigger_manager.add_variable("kills", 3)
    t = scn.trigger_manager.add_trigger("Archer down")
    t.new_condition.destroy_object(unit_object=archer.reference_id)
    t.new_effect.send_chat(source_player=PlayerId.ONE, message="The archer fell.")
    return scenarios.save(scn, path), archer


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    d = tmp_path_factory.mktemp("triggers")
    src, archer = with_triggers(str(d / "trig.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(d / "World"))
    return str(d / "World"), (archer.unit_const, archer.x, archer.y)


def summary(scn):
    tm = scn.trigger_manager
    return ([(t.name, [(c.condition_type, c.unit_object) for c in t.conditions],
              [(e.effect_type, e.message) for e in t.effects]) for t in tm.triggers],
            [(v.variable_id, v.name) for v in tm.variables])


def by_ref(scn):
    return {u.reference_id: (u.unit_const, u.x, u.y) for p in scn.unit_manager.units for u in p}


def test_export_gives_the_triggers_and_the_object_of_the_condition(world, tmp_path):
    path, archer = world
    src = read(os.path.join(path, json.load(open(os.path.join(path, "aoe2mc.json")))["source"]))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        scn = read(export.export(path, str(tmp_path / "back.aoe2scenario")))
    assert summary(scn) == summary(src) and scn.trigger_manager.triggers
    ref = scn.trigger_manager.triggers[0].conditions[0].unit_object
    assert by_ref(scn)[ref] == archer
    assert "is not in the export" not in out.getvalue()


def test_placed_objects_get_ids_above_the_source(world, tmp_path):
    path, _ = world
    save = tmp_path / "save"
    shutil.copytree(path, save / "world")
    with open(save / savegame.FILE, "w") as f:
        json.dump({"placed": [{"id": UnitInfo.MILITIA.ID, "player": 1, "tile": [9.5, 9.5]}]}, f)
    data = json.load(open(os.path.join(path, "aoe2mc.json")))
    top = max(o["ref"] for o in data["objects"] if o.get("ref") is not None)
    with contextlib.redirect_stdout(io.StringIO()):
        refs = by_ref(read(export.export(str(save), str(tmp_path / "placed.aoe2scenario"))))
    assert [r for r, u in refs.items() if u[0] == UnitInfo.MILITIA.ID] == [top + 1]
    assert {o["ref"] for o in data["objects"]} <= set(refs)


def test_a_removed_object_keeps_its_trigger_and_prints_a_line(world, tmp_path):
    path, archer = world
    data = json.load(open(os.path.join(path, "aoe2mc.json")))
    i = next(i for i, o in enumerate(data["objects"]) if o["id"] == archer[0])
    save = tmp_path / "save"
    shutil.copytree(path, save / "world")
    with open(save / savegame.FILE, "w") as f:
        json.dump({"placed": [], "removed": [i]}, f)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        scn = read(export.export(str(save), str(tmp_path / "gone.aoe2scenario")))
    assert [t.name for t in scn.trigger_manager.triggers] == ["Archer down"]
    lines = [x for x in out.getvalue().splitlines() if "is not in the export" in x]
    assert len(lines) == 1 and "Archer down" in lines[0]


def test_a_scenario_with_no_triggers_exports_as_before(tiny_world, tmp_path):
    path = tiny_world[0]
    assert json.load(open(os.path.join(path, "aoe2mc.json")))["source"] == aoe2mc.SOURCE
    plain = tmp_path / "plain"
    shutil.copytree(path, plain)
    data = json.load(open(plain / "aoe2mc.json"))
    del data["source"]
    json.dump(data, open(plain / "aoe2mc.json", "w"))
    a = read(export.export(path, str(tmp_path / "a.aoe2scenario")))
    b = read(export.export(str(plain), str(tmp_path / "b.aoe2scenario")))
    assert not a.trigger_manager.triggers and not a.trigger_manager.variables
    assert sorted(by_ref(a).items()) == sorted(by_ref(b).items())


def test_only_a_de_scenario_is_copied(tmp_path):
    (tmp_path / aoe2mc.SOURCE).write_bytes(b"old")                  # of an earlier conversion
    assert aoe2mc.copy_source(None, str(tmp_path)) is None          # --random-map
    assert aoe2mc.copy_source(str(tmp_path / "map.rms"), str(tmp_path)) is None
    assert not (tmp_path / aoe2mc.SOURCE).exists()
