"""The light state of the editor (#6012): menus and clicks, build.free, and the placed objects in the save."""
import contextlib
import io
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import build  # noqa: E402
import editor  # noqa: E402
import menu  # noqa: E402
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario  # noqa: E402
from test_editor import FakeGame  # noqa: E402


class ClickGame(FakeGame):
    """A fake game whose player clicked slot 3 once."""
    def command(self, cmd):
        self.sent.append(cmd)
        if cmd.startswith("scoreboard players get") and menu.OBJECTIVE in cmd and not any("reset" in c for c in self.sent):
            return "p has 4 [x]"
        return ""


def test_a_menu_click_reaches_its_handler(tiny_world):
    state = editor.State(ClickGame(tiny_world[0]))
    got = []
    menu.show(state, "p", "Editor", [], lambda player, slot, shift: got.append((player, slot, shift)))
    assert editor.tick(state) == [("p", 3)] and got == [("p", 3, False)]


def test_build_free_works_on_the_state(tiny_world):
    state = editor.State(FakeGame(tiny_world[0]))
    x, z = next((x, z) for z in range(state.map.n) for x in range(state.map.n) if state.map.free(x, z))
    assert build.free(state, (x, x + 1, z, z + 1))
    state.map.blocked.add((x, z))
    assert not build.free(state, (x, x + 1, z, z + 1))


def test_a_placed_object_is_in_the_save_and_the_scenario(tiny_world, tmp_path):
    world = str(tmp_path / "w")
    shutil.copytree(tiny_world[0], world)
    data = json.load(open(os.path.join(world, "aoe2mc.json")))
    data["turn"] = 0
    json.dump(data, open(os.path.join(world, "aoe2mc.json"), "w"))
    state = editor.State(FakeGame(world))
    state.place(83, 2, (5.5, 6.5))                                  # a villager of player 2
    out = str(tmp_path / "out.aoe2scenario")
    with contextlib.redirect_stdout(io.StringIO()):
        editor.save(state.game, out, state)
    saves = os.path.join(tmp_path, "saves")
    folder = os.path.join(saves, os.listdir(saves)[0])
    assert json.load(open(os.path.join(folder, "savegame.json")))["placed"] == [{"id": 83, "player": 2, "tile": [5.5, 6.5]}]
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(out)
    units = [(u.unit_const, round(u.x, 1), round(u.y, 1)) for u in scn.unit_manager.units[2]]
    assert (83, 5.5, 6.5) in units
