"""#4531: the embedded AI script of a scenario player goes into its row of aoe2mc.json "players", and its bot in the
scenario mode plays by it (run.bot_script)."""
import contextlib
import io
import json
import shutil

from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from test_bot_gather import bot_map
from test_per_bot import queued

import aoe2mc
from game import per, run
from game.bot import build, train  # noqa: F401                    # the modules that per uses
from tools import scenarios

SCRIPT = "(defrule (civilian-population < 10) (can-train villager) => (train villager))"


def players(tmp_path):
    src = scenarios.tiny(str(tmp_path / "t.aoe2scenario"))
    shutil.copy(src, tmp_path / "read.aoe2scenario")              # the parser does not overwrite its source
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(str(tmp_path / "read.aoe2scenario"))
    p = scn.player_manager.players[2]
    p.personality, p.ai_script = "rusher", SCRIPT
    out = scenarios.save(scn, str(tmp_path / "s.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(out, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        return json.load(f)["players"]


def test_the_embedded_script_goes_to_the_bot_of_player_2(tmp_path):
    rows = players(tmp_path)
    assert rows["2"]["ai"] == SCRIPT and "ai" not in rows["1"]
    server, me, b = bot_map()                                          # the bot plays player 2
    b.script = per.Script(run.bot_script(rows, 2, ["other.per"], 0), b)   # the scenario script wins over --ai
    b.g.stock.update(food=1000, wood=1000, gold=1000, stone=1000)
    b.step()
    assert queued(b) == {"VILLAGER_MALE"}


def test_a_player_without_a_script_takes_the_ai_file_or_none(tmp_path):
    f = tmp_path / "a.per"
    f.write_text(SCRIPT)
    assert run.bot_script({"2": {}}, 2, [str(f)], 0) and run.bot_script({"2": {}}, 2, None, 0) is None
