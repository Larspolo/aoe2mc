"""Live replay: the game type of the record in the score panel title and the summary (#4833). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

LOBBY = {"type": "Test Type", "dataset": "Test Set", "starting_age": "Test Age", "population": 123}


def made(lobby=None):
    d = data([])
    if lobby:
        d["lobby"] = lobby
    return replay.Replay(Fake(), d)


def test_the_panel_title_and_the_summary_name_the_game_type_and_the_data_set():
    r = made(LOBBY)
    title = r.score_commands()[0]
    assert title.startswith("scoreboard objectives add aoe_pop dummy") and LOBBY["type"] in title
    line = r.summary_commands()[1]
    assert line.startswith("tellraw @a") and all(str(v) in line for v in LOBBY.values())


def test_no_lobby_keeps_the_texts():
    r = made()
    assert r.score_commands()[0] == 'scoreboard objectives add aoe_pop dummy "Population"'
    assert not any("Test" in c for c in r.summary_commands())
    assert made({"type": None}).score_commands()[0].endswith('"Population"')
