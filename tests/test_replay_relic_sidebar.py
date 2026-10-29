"""Live replay: the sidebar name of a player shows its relics in the monasteries (#4011)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402


def names(cmds, p=1):
    return [json.loads(c.split(" ", 6)[6])["text"] for c in cmds if f" display name P{p} " in c]


def game():
    r = replay.Replay(Fake(), data([]))
    r.pop, r.ages = {1: 1, 2: 1}, {1: "Dark", 2: "Dark"}
    r.relics = {30: dict(home=(1, 2, 3, 4), player=1), 31: dict(home=(5, 6, 7, 8), player=1),
                32: dict(home=None, player=2)}
    return r


def test_the_display_name_holds_the_relics_of_the_player():
    r = game()
    assert names(r.score_commands(), 1) == ["Player 1 (Britons) · Dark · F 200 W 200 G 100 S 200 (est.) · Relics 2"]


def test_a_player_with_no_relic_has_no_relic_part():
    r = game()
    assert names(r.score_commands(), 2) == ["Player 2 (Aztecs) · Dark · F 200 W 200 G 100 S 200 (est.)"]


def test_a_second_call_with_no_change_sends_no_name():
    r = game()
    r.score_commands()
    assert names(r.score_commands(), 1) == [] and names(r.score_commands(), 2) == []
