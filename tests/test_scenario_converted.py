"""#2673 (epic #2538, criterion 2): the full path of the scenario mode. The converter writes the start values and the
texts of the `triggers` scenario into aoe2mc.json, and scenario.setup and scenario.tick use them in a game."""
import contextlib
import io
import json
import os
import shutil
import sys

from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import gather  # noqa: E402
import scenario  # noqa: E402
import scenarios  # noqa: E402
import train  # noqa: E402
from test_gather import FakeServer  # noqa: E402

import aoe2mc  # noqa: E402

START = {"food": 321, "wood": 432, "gold": 543, "stone": 654}


def converted(tmp_path):
    """aoe2mc.json of the triggers scenario with the start values of player 1, an instruction text and an objective."""
    src = scenarios.triggers(str(tmp_path / "t.aoe2scenario"))
    shutil.copy(src, tmp_path / "read.aoe2scenario")              # the parser does not overwrite its source
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(str(tmp_path / "read.aoe2scenario"))
    p = scn.player_manager.players[1]
    for r, v in START.items():
        setattr(p, r, v)
    p.population_cap = 75
    scn.message_manager.instructions = "Bring the knight to the hill."
    t = scn.trigger_manager.triggers[1]                           # "Knight on the hill": an objective of the game
    t.display_as_objective, t.description = True, "Hold the hill."
    out = scenarios.save(scn, str(tmp_path / "s.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(out, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        return json.load(f)


def test_a_converted_scenario_starts_with_its_values_and_its_book(tmp_path):
    data = converted(tmp_path)
    assert data["players"]["1"]["resources"] == START and data["players"]["1"]["pop_limit"] == 75
    server = FakeServer({})
    g = gather.Gather(server, data).setup()
    g.bots = []
    scenario.setup(g, "scenario")
    assert g.stock == START and train.max_pop(g) == 75
    assert f"scoreboard players set Food {g.board} 321" in server.log
    command = server.command

    def answer(cmd):                                              # a person with no book is online
        if cmd.startswith("execute if entity @a[tag=!aoe_book]"):
            server.log.append(cmd)
            return "Test passed, count: 1"
        return command(cmd)
    server.command = answer
    g.clock = lambda: 0.0
    scenario.tick(g)
    books = [c for c in server.log if c.startswith("item replace") and "written_book" in c]
    assert len(books) == 1 and "- Hold the hill." in books[0] and "Bring the knight to the hill." in books[0]
    assert "tellraw @a[tag=!aoe_book] " + json.dumps({"text": "Bring the knight to the hill.", "color": "gold"}) in server.log
