"""Live replay: the build order of each player in the sky, below the army texts (#4049). Fake RCON."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402


def make(timeline=()):
    return replay.Replay(Fake(), data(list(timeline)))


def shown(cmd):
    """The text component of a build order command (a summon or a data merge)."""
    return json.loads(re.search(r"text:(\{[^}]*\})", cmd)[1])


def build(t, name, player=1):
    return {"time": t, "player": player, "kind": "build", "name": name}


def test_the_first_call_summons_one_text_per_player_and_a_second_call_sends_nothing():
    r = make([build(60000, "HOUSE")])
    first = r.build_order_view(60000)
    assert len(first) == 2 and all(c.startswith("summon text_display") for c in first)
    assert f'"{replay.ORDER}.1"' in first[0] and f'"{replay.ORDER}.2"' in first[1]
    assert shown(first[0]) == {"text": "Player 1 (Britons): 01:00 House", "color": r.label(1)[1]}
    assert shown(first[1])["text"] == "Player 2 (Aztecs): -"
    assert r.build_order_view(60000) == []


def test_a_new_step_changes_the_text_of_its_player_only():
    r = make([build(60000, "HOUSE"), build(90000, "MILL")])
    r.build_order_view(60000)
    (merge,) = r.build_order_view(90000)
    assert merge.startswith(f"data merge entity @e[type=text_display,tag={replay.ORDER}.1,limit=1] ")
    assert shown(merge)["text"] == "Player 1 (Britons): 01:00 House · 01:30 Mill"


def test_the_line_shows_at_most_4_steps():
    names = ["HOUSE", "MILL", "LUMBER_CAMP", "BARRACKS", "BLACKSMITH"]
    r = make([build(60000 * (i + 1), n) for i, n in enumerate(names)])
    line = shown(r.build_order_view(600000)[0])["text"]
    assert line.count(" · ") == 3 and "House" not in line and line.endswith("05:00 Blacksmith")
