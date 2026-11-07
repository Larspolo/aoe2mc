"""The trigger menu of the editor (#6088): the clicks change the triggers of the scenario of the world (State.scenario),
and the save writes them, with the triggers of the source scenario once and with all their fields."""
import contextlib
import io
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import editor  # noqa: E402
import export  # noqa: E402
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario  # noqa: E402
from test_editor import FakeGame, Server  # noqa: E402
from test_editor_palette import state_of  # noqa: E402

import aoe2mc  # noqa: E402


def world_of(tiny_world, tmp_path):
    world = str(tmp_path / "w")
    shutil.copytree(tiny_world[0], world)
    return world


def read(path):
    with contextlib.redirect_stdout(io.StringIO()):
        return AoE2DEScenario.from_file(path)


def saved(s, tmp_path):
    out = str(tmp_path / "out.aoe2scenario")
    with contextlib.redirect_stdout(io.StringIO()):
        editor.save(s.game, out, s)
    return read(out)


def click(s, slot, shift=False):
    s.menus["p"]("p", slot, shift)


def names(s):
    return [t.name for t in s.scenario.trigger_manager.triggers]


def test_clicks_add_switch_loop_and_remove_triggers(tiny_world, tmp_path):
    s = state_of(world_of(tiny_world, tmp_path))
    before = len(names(s))
    editor.triggers_menu(s, "p")
    click(s, editor.ADD)
    click(s, editor.ADD)
    assert names(s)[before:] == [f"Trigger {before}", f"Trigger {before + 1}"] and s.edited
    ts = s.scenario.trigger_manager.triggers
    on = ts[before].enabled
    click(s, before, shift=True)                                      # the list: a shift click turns it on or off
    assert ts[before].enabled != on
    click(s, before + 1)                                              # open the second new trigger
    click(s, editor.LOOP)
    assert ts[before + 1].looping
    click(s, editor.TRIGGER)
    click(s, editor.TRIGGER)
    assert ts[before + 1].enabled                                     # two clicks: on again
    click(s, editor.DROP)                                             # no shift: no remove
    assert len(names(s)) == before + 2
    click(s, editor.DROP, shift=True)
    assert names(s)[before:] == [f"Trigger {before}"]
    click(s, editor.ADD)                                              # the remove went back to the list
    assert len(names(s)) == before + 2


def test_the_save_keeps_the_source_triggers_once_with_their_fields(tiny_world, tmp_path):
    world = world_of(tiny_world, tmp_path)
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    src = os.path.join(world, data.get("source") or aoe2mc.SOURCE)
    scn = read(src)
    t = scn.trigger_manager.add_trigger("Greet", description="say hello", looping=True)
    t.new_condition.timer(timer=7)
    t.new_effect.send_chat(source_player=1, message="hello")
    export.scenarios.save(scn, src, name=os.path.basename(src))      # the parser writes no file over its own source
    data["source"] = os.path.basename(src)
    with open(os.path.join(world, "aoe2mc.json"), "w") as f:
        json.dump(data, f)
    s = state_of(world)
    editor.triggers_menu(s, "p")
    click(s, editor.ADD)
    out = saved(s, tmp_path).trigger_manager.triggers
    assert [t.name for t in out].count("Greet") == 1 and out[-1].name == f"Trigger {len(out) - 1}"
    g = next(t for t in out if t.name == "Greet")
    assert g.description == "say hello" and g.looping
    assert g.conditions[0].timer == 7 and g.effects[0].message == "hello" and g.effects[0].source_player == 1
    assert [t.name for t in read(src).trigger_manager.triggers].count(f"Trigger {len(out) - 1}") == 0   # the editor world: no change


def test_a_world_with_no_source_gets_one(tiny_world, tmp_path):
    world = world_of(tiny_world, tmp_path)
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    if data.pop("source", None):
        os.remove(os.path.join(world, aoe2mc.SOURCE))
    with open(os.path.join(world, "aoe2mc.json"), "w") as f:
        json.dump(data, f)
    s = state_of(world)
    assert "scenario" not in vars(s)                                  # no trigger change: the scenario does not load
    saved(s, tmp_path)
    assert "scenario" not in vars(s) and not s.data.get("source")
    assert names(s) == []
    editor.triggers_menu(s, "p")
    click(s, editor.ADD)
    assert [t.name for t in saved(s, tmp_path).trigger_manager.triggers] == ["Trigger 0"]
    assert not os.path.exists(os.path.join(world, aoe2mc.SOURCE))     # only the save folder has it


def test_the_chat_word_opens_the_menu(tiny_world, tmp_path):
    game = FakeGame(world_of(tiny_world, tmp_path))
    game.server = Server([])
    s = editor.State(game)
    s.menus = {}

    def alive():                                                      # the chat line after the start, then one tick
        game.server.log.append("[12:00:00] [Server thread/INFO]: <p> triggers")
        return len(game.server.log) < 2
    with contextlib.redirect_stdout(io.StringIO()):
        editor.run(game, str(tmp_path / "out.aoe2scenario"), alive, s)
    assert "p" in s.menus and any(c.startswith("aoe menu p Triggers") for c in game.sent)
