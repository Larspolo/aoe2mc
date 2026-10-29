"""Live replay: the army at the end and the losses by type in the chat summary (#3697). Fake RCON."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402


def military_lines(r):
    """The text of each military line of the summary, player 1 first."""
    lines = [c for c in r.summary_commands() if "military units" in c]
    return ["".join(t["text"] for t in json.loads(c.split(" ", 2)[2])) for c in lines]


def test_the_army_and_the_losses_name_each_type_most_first():
    r = replay.Replay(Fake(), data([]))
    r.army = {1: 3, 2: 1}
    r.troops = {1: {"KNIGHT": 8, "CROSSBOWMAN": 12, "ARCHER": 0}, 2: {"ARCHER": 0}}
    r.fallen = {1: {"ARCHER": 2, "KNIGHT": 5}}
    texts = military_lines(r)
    assert texts[0].endswith("buildings lost 0, army at the end: 12 Crossbowman, 8 Knight, lost: 5 Knight, 2 Archer")
    assert texts[1] == "Player 2 (Aztecs): military units trained 1, units lost 0, buildings lost 0"


def test_more_than_six_types_show_the_rest_as_a_count():
    r = replay.Replay(Fake(), data([]))
    r.army = {1: 1}
    r.troops = {1: {f"UNIT_{i}": i + 1 for i in range(7)}}
    text = military_lines(r)[0]
    assert text.endswith("army at the end: 7 Unit 6, 6 Unit 5, 5 Unit 4, 4 Unit 3, 3 Unit 2, 2 Unit 1, +1")
