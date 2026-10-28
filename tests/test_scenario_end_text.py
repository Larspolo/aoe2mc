"""#3298 (epic #2538): at the end of a game each person reads the "victory" or the "loss" text of the scenario in the
chat (the tab "Messages" of the scenario editor). A text with AoE2 color tags shows without them."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import cheats  # noqa: E402
import scenario  # noqa: E402
from test_scenario_mode import game  # noqa: E402


def ended(messages):
    server, g, _ = game({"0": {}, "1": {}, "2": {}})
    g.data["messages"] = messages
    start = len(server.log)
    cheats.over(g, lambda n: n == 1)
    return server.log[start:]


def test_the_winner_reads_the_victory_text_and_the_loser_the_loss_text():
    log = ended({"victory": "You saved the town.", "loss": "The town fell."})
    assert scenario.chat("@a[team=p1]", "You saved the town.")[0] in log
    assert scenario.chat("@a[team=p2]", "The town fell.")[0] in log
    assert not any("The town fell." in c and "team=p1" in c for c in log)


def test_a_text_with_color_tags_shows_without_them():
    log = ended({"victory": "You saved the <BLUE>town</BLUE>.", "loss": "The town fell."})
    assert scenario.chat("@a[team=p1]", "You saved the town.")[0] in log
    assert not any("<BLUE>" in c for c in log)


def test_a_game_with_no_messages_sends_no_extra_command():
    assert not any('"color": "gold"' in c for c in ended({}))
    assert not any('"color": "gold"' in c for c in ended({"hints": "Build a farm."}))
