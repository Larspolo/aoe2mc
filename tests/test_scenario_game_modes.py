"""#3297 (epic #2538): the secondary game modes of a scenario (tab "Global Victory": Empire Wars, Sudden Death,
Regicide, King of the Hill) go into aoe2mc.json "victory" "modes", and a scenario game turns them on as the lobby
options do."""
import contextlib
import io
import json
import os
import sys

from AoE2ScenarioParser.datasets.trigger_lists import SecondaryGameMode, VictoryCondition

import aoe2mc
from tools import scenarios

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import run  # noqa: E402
import scenario  # noqa: E402
from test_scenario_mode import game  # noqa: E402

PLAYERS = {"0": {}, "1": {"resources": {"food": 100}}, "2": {}}


def victory(tmp_path, modes, condition=VictoryCondition.SECONDARY_GAME_MODE):
    scn = scenarios.new_scenario(24)
    scn.option_manager.victory_condition = condition
    scn.option_manager.secondary_game_modes = modes
    src = scenarios.save(scn, str(tmp_path / "v.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        return json.load(f).get("victory")


def test_regicide_and_sudden_death_go_into_the_victory(tmp_path):
    modes = SecondaryGameMode.REGICIDE | SecondaryGameMode.SUDDEN_DEATH
    assert victory(tmp_path, modes) == {"condition": "secondary-game-mode", "modes": ["regicide", "sudden-death"]}


def test_no_secondary_mode_writes_no_modes(tmp_path):
    assert victory(tmp_path, SecondaryGameMode.NONE, VictoryCondition.CONQUEST) == {"condition": "conquest"}


def test_a_scenario_game_turns_on_the_modes_as_the_lobby_options():
    settings = run.mode_defaults({**run.SETTINGS, "mode": "scenario"})
    run.scenario_modes(settings, {"victory": {"condition": "secondary-game-mode", "modes": ["regicide", "sudden-death"]}})
    assert (settings["regicide"], settings["sudden_death"], settings["empire_wars"]) == (True, True, False)


def test_a_lobby_option_stays_on_and_other_modes_change_nothing():
    settings = run.mode_defaults({**run.SETTINGS, "mode": "standard", "empire_wars": True})
    run.scenario_modes(settings, {"victory": {"condition": "secondary-game-mode", "modes": ["regicide"]}})
    assert (settings["regicide"], settings["empire_wars"]) == (False, True)     # only the scenario mode reads them
    settings["mode"] = "scenario"
    run.scenario_modes(settings, {})
    assert settings["empire_wars"] and not settings["regicide"]


def test_king_of_the_hill_uses_the_victory_of_hill():
    _, g, bot = game(PLAYERS)
    g.data["victory"] = {"condition": "secondary-game-mode", "modes": ["king-of-the-hill"]}
    scenario.setup(g, "scenario")
    assert g.victory == bot.victory == "king-of-the-hill"


def test_the_other_secondary_modes_end_by_conquest():
    _, g, _ = game(PLAYERS)
    g.data["victory"] = {"condition": "secondary-game-mode", "modes": ["regicide"]}
    scenario.setup(g, "scenario")
    assert g.victory == "conquest" and g.victory in run.VICTORIES
