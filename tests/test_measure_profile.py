"""The time and the RCON profile of tools/measure_clicks.py (#5871): the result time is the first command or input
after which done() is true, not the next step of the game loop."""
import os
import sys
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import measure_clicks as mc  # noqa: E402

from game import gather  # noqa: E402


def test_recorder_sets_the_hit_at_the_first_command_after_the_result():
    state = {"done": False}
    game = NS(command=lambda cmd: state.update(done=state["done"] or cmd == "tag u add sel") or "")
    g = NS(inputs=lambda: [], click=lambda name: None)
    r = mc.Recorder(game, g)
    r.done, r.on = lambda: state["done"], True
    game.command("list")
    assert r.hit is None
    game.command("tag u add sel")
    assert r.hit is not None
    assert [c for _, _, c in r.log] == ["list", "tag u add sel"]


def test_recorder_checks_after_inputs_and_click():
    state = {"done": False}
    g = NS(inputs=lambda: state.update(done=True) or ["aoe2mc"], click=lambda name: None)
    r = mc.Recorder(NS(command=lambda cmd: ""), g)
    r.done, r.on = lambda: state["done"], True
    assert g.inputs() == ["aoe2mc"] and r.hit is not None


def test_recorder_is_off_outside_a_try():
    game = NS(command=lambda cmd: "ok")
    r = mc.Recorder(game, NS(inputs=list, click=print))
    assert game.command("list") == "ok" and r.log == []


def test_kind_hides_numbers_the_player_and_uuids():
    assert mc.kind("data get entity 0a1b2c3d-0000-1111-2222-333344445555 Pos") == "data get entity X Pos"
    assert mc.kind(f"tp {mc.NAME} 4.5 66 -7") == "tp X N N N"


def test_profile_counts_the_commands_from_the_input_to_the_result():
    log = [(1.00, 0.002, "execute if entity @a[scores={aoe_input=1..}]"),
           (1.05, 0.002, f"scoreboard players reset {mc.NAME} {gather.INPUT_SCORE}"),
           (1.06, 0.004, f"data get entity {mc.NAME} Pos"), (1.07, 0.004, f"data get entity {mc.NAME} Pos"),
           (1.20, 0.004, "data get entity c Pos")]
    lines = mc.profile("Click", [(1.0, 1.1, 1.3, log)])
    assert "then 2 commands up to the result" in lines[2] and "RCON 8 ms" in lines[2]
    assert "| `data get entity X Pos` | 2.0 |" in lines
    assert "No try" in mc.profile("Click", [(1.0, None, 1.3, log)])[2]
