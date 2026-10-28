"""#2762 (epic #2538): the trigger effects "Lock Gate" and "Unlock Gate". The converter puts the order "lock <ref>" or
"unlock <ref>" into the data storage aoe2mc:orders; the scenario mode of the game program puts the portcullis on the
converted gate and locks or unlocks it with the Paper plugin (`aoe gate lock|unlock X Z`, Gates.java)."""
import os
import shutil
import sys
import time
import types

import numpy as np
import pytest

import aoe2mc
from tools import triggers

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import scenario  # noqa: E402
from test_plugin import pos  # noqa: E402
from test_scenario_mode import game  # noqa: E402

STORED = "Storage aoe2mc:orders has the following contents: "
GATE = {"kind": "building", "name": "GATE_NORTHWEST_TO_SOUTHEAST", "ref": 26, "player": 1, "footprint": [8, 4, 24, 8],
        "tile": [4.0, 1.5]}


def trigger(kind, refs=(26,)):
    e = dict(type=kind, message="", player=1, time=0, object=None, tile=[-1, -1], area=[-1] * 4, selected=list(refs))
    return dict(id=8, name="Gate", enabled=True, looping=False,
                conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)], effects=[e])


def test_the_trigger_function_stores_the_lock_and_the_unlock():
    for kind, order in ((aoe2mc.LOCK_GATE, "lock"), (aoe2mc.UNLOCK_GATE, "unlock")):
        _, files = aoe2mc.trigger_files([trigger(kind, (26, 35))], 4, np.full((64, 64), 70, np.int16))
        assert files["data/aoe2mc/function/trigger/8.mcfunction"].splitlines()[:2] == [
            f'data modify storage aoe2mc:orders list append value "{order} {r}"' for r in (26, 35)]
    assert aoe2mc.trigger_files([trigger(aoe2mc.LOCK_GATE, ())])[1] == {}   # no gate: no trigger


def play(*storage, objects=(GATE,)):
    """Run scenario.orders once for each storage text with a fake RCON on Paper. Returns the commands."""
    server, g, _ = game({"1": {}})
    g.paper, g.data["objects"] = True, list(objects)
    command, log = server.command, []

    def answer(cmd):
        log.append(cmd)
        return stored if cmd.startswith("data get storage aoe2mc:orders") else command(cmd)
    server.command = answer
    for stored in storage:
        scenario.orders(g)
    return log


def test_a_lock_puts_the_portcullis_once_and_locks_the_gate():
    log = play(STORED + '["lock 26"]', STORED + '["unlock 26"]', STORED + '["lock 26"]')
    gates = [c for c in log if c.startswith("aoe gate")]
    assert gates[0].startswith("aoe gate p1 ") and gates[1:] == ["aoe gate lock 16 6", "aoe gate unlock 16 6",
                                                                  "aoe gate lock 16 6"]
    bars = [i for i, c in enumerate(log) if c.endswith("iron_bars")]
    assert bars and max(bars) < log.index("aoe gate lock 16 6")           # the portcullis once, before the first lock


def test_no_gate_or_a_diagonal_gate_gives_no_command():
    diagonal = dict(GATE, name="GATE_NORTH_TO_SOUTH", footprint=[8, 4, 24, 20])
    assert not [c for c in play(STORED + '["lock 99"]') if c.startswith("aoe gate")]
    assert not [c for c in play(STORED + '["lock 26"]', objects=(diagonal,)) if c.startswith("aoe gate")]


def test_the_map_rows_name_the_commands_and_the_issue():
    for kind, word in (("LOCK_GATE", "aoe gate lock"), ("UNLOCK_GATE", "aoe gate unlock")):
        assert word in triggers.MAP[("effect", kind)] and "#2762" in triggers.MAP[("effect", kind)]


@pytest.mark.mc
def test_a_locked_gate_stays_closed_for_an_own_unit(tiny_world, tmp_path):
    from test_paper import paper_reachable
    from game import build, run
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0, n = 1, 200, 1, 30                                       # a floor in the air (test_gate_open.py)
    gx, wz = x0 + 8, z0 + 12
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + n + 2} {z0 + n + 2}")
        game.command(f"fill {x0} {y - 1} {z0} {x0 + n} {y - 1} {z0 + n} stone_bricks")
        game.command(f"fill {x0} {y} {wz} {x0 + n} {y + 3} {wz} stone")
        game.command(f"fill {gx + 1} {y} {wz} {gx + 2} {y + 2} {wz} air")
        game.command("team add p1")
        g = types.SimpleNamespace(command=game.command, paper=True, map=types.SimpleNamespace(T=1, y=lambda x, z: y))
        build.portcullis(g, {"name": "PALISADE_GATE", "player": 1, "footprint": (gx, gx + 4, wz, wz + 1)})
        assert game.command(f"aoe gate lock {gx + 2} {wz}").strip() == "Locked 1 gates"
        game.command(f'summon zombie {gx + 1.5} {y} {wz - 8 + 0.5} {{NoAI:1b,IsBaby:0b,Tags:["own"]}}')
        game.command("team join p1 @e[tag=own]")
        game.command(f"aoe moveto @e[tag=own] {gx + 1.5} {y} {wz + 8 + 0.5}")
        time.sleep(12)
        assert pos(game, "own")[2] < wz, pos(game, "own")                # the own unit stays north of the locked gate
        assert "passed" in game.command(f"execute if block {gx + 1} {y} {wz} minecraft:iron_bars")
        assert game.command(f"aoe gate unlock {gx + 2} {wz}").strip() == "Unlocked 1 gates"
        game.command(f"aoe moveto @e[tag=own] {gx + 1.5} {y} {wz + 8 + 0.5}")
        end = time.time() + 30
        while time.time() < end and not (pos(game, "own") and pos(game, "own")[2] > wz + 6):
            time.sleep(0.2)
        assert pos(game, "own")[2] > wz + 6, pos(game, "own")            # through the unlocked gate
