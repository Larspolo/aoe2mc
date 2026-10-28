"""#2567 (epic #2538): in the scenario mode the victory setting of the scenario (aoe2mc.json "victory", #2566) ends
the game, not --victory: "custom" leaves the end to the triggers."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import conquest  # noqa: E402
import scenario  # noqa: E402
from test_scenario_mode import game  # noqa: E402

PLAYERS = {"0": {}, "1": {"resources": {"food": 100}}, "2": {}}


def test_the_time_limit_of_the_scenario_replaces_the_lobby_setting():
    _, g, bot = game(PLAYERS)
    g.data["victory"] = {"condition": "time-limit", "years": 300}
    scenario.setup(g, "scenario")
    assert (g.victory, g.victory_value) == (bot.victory, bot.victory_value) == ("time-limit", 300)


def test_a_score_target_goes_into_the_victory_value():
    _, g, _ = game(PLAYERS)
    g.data["victory"] = {"condition": "score", "score": 9000}
    scenario.setup(g, "scenario")
    assert (g.victory, g.victory_value) == ("score", 9000)


def test_custom_gives_no_conquest_end():
    _, g, _ = game(PLAYERS)
    g.data["victory"] = {"condition": "custom"}
    scenario.setup(g, "scenario")
    g.conquest_seen = {1, 2}                                           # both had units: now none is left
    conquest.tick(g)
    assert g.ended is None and not vars(g).get("defeated")


def test_a_world_without_victory_keeps_the_lobby_setting():
    _, g, _ = game(PLAYERS)
    g.victory, g.victory_value = "conquest", None
    scenario.setup(g, "scenario")
    assert (g.victory, g.victory_value) == ("conquest", None)
