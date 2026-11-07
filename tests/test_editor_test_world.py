"""The chat word `test` of the editor (#6081): save the map and convert it into a fresh test world."""
import contextlib
import io
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import editor  # noqa: E402
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario  # noqa: E402
from test_editor_palette import state_of  # noqa: E402


def quiet(f, *a):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return f(*a)


def scene(path):
    """The terrain, objects and players of a scenario (the file also has a time stamp)."""
    scn = quiet(AoE2DEScenario.from_file, path)
    return ([(t.x, t.y, t.terrain_id, t.elevation) for t in scn.map_manager.terrain],
            sorted((u.unit_const, u.player.value, u.x, u.y) for u in scn.unit_manager.get_all_units()),
            [(p.civilization, p.food, p.wood, p.gold, p.stone) for p in scn.player_manager.players])


def test_the_test_world_has_the_objects_and_players_of_the_editor(tiny_world, tmp_path):
    world = str(tmp_path / "w")
    shutil.copytree(tiny_world[0], world)
    s = state_of(world)
    s.data["players"]["2"]["resources"]["food"] = 777
    os.makedirs(world + "-test")
    open(os.path.join(world + "-test", "old"), "w").close()        # an old test world goes away
    out = str(tmp_path / "out.aoe2scenario")
    got = quiet(editor.test_world, s.game, out, s)
    assert got == world + "-test" and not os.path.exists(os.path.join(got, "old"))
    with open(os.path.join(got, "aoe2mc.json")) as f:
        data = json.load(f)
    assert data["players"]["2"]["resources"]["food"] == 777
    names = sorted(o["name"] for o in data["objects"])
    assert names and names == sorted(o["name"] for o in s.data["objects"] if o["name"] in names)
    assert any("aoe2mc.editor.converting" in c for c in s.game.sent)
    assert any("aoe2mc.editor.test" in c and "--play --mode scenario" in c for c in s.game.sent)


def test_the_editor_world_has_no_change(tiny_world, tmp_path):
    world = str(tmp_path / "w")
    shutil.copytree(tiny_world[0], world)
    s = state_of(world)
    a, b = str(tmp_path / "a.aoe2scenario"), str(tmp_path / "b.aoe2scenario")
    quiet(editor.save, s.game, a, s)
    quiet(editor.test_world, s.game, str(tmp_path / "t.aoe2scenario"), s)
    quiet(editor.save, s.game, b, s)
    assert scene(a) == scene(b)


def test_run_calls_test_world_for_the_chat_word(monkeypatch):
    from test_editor import FakeGame
    game, calls, n = FakeGame("w"), [], iter([True, False])
    game.server.log = ["[12:00:00 INFO]: <Steve> tests", "[12:00:01 INFO]: <Steve> test"]
    game.server.log, log = [], game.server.log
    monkeypatch.setattr(editor, "test_world", lambda g, out, st: calls.append(out) or "w-test")
    monkeypatch.setattr(editor.time, "sleep", lambda s: None)
    state = type("S", (), {"menus": {}})()

    def alive():
        game.server.log[:] = log
        return next(n)
    quiet(editor.run, game, "o.aoe2scenario", alive, state)
    assert calls == ["o.aoe2scenario"]
