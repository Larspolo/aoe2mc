"""A loaded game of the scenario mode keeps the victory setting of the scenario and the population limit of each player
(epic #2538): the mode starts again in a loaded game with start False, so the save keeps the stock and the scores."""
import json

import run  # noqa: E402
import savegame  # noqa: E402
import scenario  # noqa: E402
import train  # noqa: E402
from test_scenario_mode import START, game

PLAYERS = {"0": {}, "1": {"resources": START, "pop_limit": 25}, "2": {"pop_limit": 125}}


def test_the_scenario_mode_starts_again_in_a_loaded_game():
    assert run.MODES["scenario"]["loaded"] == "start"


def test_a_loaded_scenario_game_keeps_the_victory_and_the_population_limit():
    _, g, bot = game(PLAYERS)
    g.data["victory"] = {"condition": "custom"}
    scenario.setup(g, "scenario")
    d = json.loads(json.dumps(savegame.dump(g), sort_keys=True))
    server, h, hbot = game(PLAYERS)
    h.data["victory"] = {"condition": "custom"}
    savegame.load(h, d)
    n = len(server.log)
    scenario.setup(h, "scenario", start=False)
    assert h.victory == "custom" and train.max_pop(h) == 25
    assert hbot.victory == "custom" and train.max_pop(hbot) == 125
    assert not any(c.startswith("scoreboard") for c in server.log[n:])
