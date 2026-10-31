"""The timeline book of the live replay: the heading of each player has its player color (the sidebar color) and, in a
team game, its team; the event lines stay black (#1643)."""
import json
import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import lang  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_timeline_book import TIMELINE, raw_book  # noqa: E402


def pages(r, end=1_500_000):
    return raw_book(r.timeline_commands(end))["pages"][1:]                # after the players page (#4670)


def test_the_heading_of_each_player_has_the_sidebar_color_and_the_lines_are_black():
    r = replay.Replay(Fake(), data(TIMELINE))
    one, two = pages(r)
    assert one["extra"][0] == {"text": "■ Player 1 (Britons)", "color": r.player(1)[1]} and r.player(1)[1] == "blue"
    assert two["extra"][0] == {"text": "■ Player 2 (Aztecs)", "color": "gold"}       # orange: the sidebar text color
    assert all("color" not in e for p in (one, two) for e in p["extra"][1:]) and "color" not in one


def test_a_team_game_names_the_team_in_the_heading():
    d = data(TIMELINE + [{"time": 900_000, "player": 3, "kind": "age", "age": "FEUDAL_AGE"}])
    d["players"].update({"1": {**d["players"]["1"], "team": 1}, "2": {**d["players"]["2"], "team": 2},
                         "3": {"civ": "FRANKS", "color": "green", "team": 1}})
    heads = [p["extra"][0] for p in pages(replay.Replay(Fake(), d))]
    assert heads == [{"text": "■ Team 1 · Player 1 (Britons)", "color": "blue"},
                     {"text": "■ Team 2 · Player 2 (Aztecs)", "color": "gold"},
                     {"text": "■ Team 1 · Player 3 (Franks)", "color": "green"}]


def test_a_next_page_of_a_player_has_no_heading():
    ages = [{"time": 60_000 * i, "player": 1, "kind": "age", "age": "FEUDAL_AGE"} for i in range(1, 15)]
    first, second = pages(replay.Replay(Fake(), data(ages)), 10**9)
    assert first["extra"][0]["color"] == "blue" and "color" not in json.dumps(second)
    assert lang.plain(second) == "12:00 Feudal Age\n13:00 Feudal Age\n14:00 Feudal Age"


def test_a_player_without_a_color_gets_a_black_heading():
    d = data(TIMELINE)
    del d["players"]["2"]["color"]
    assert pages(replay.Replay(Fake(), d))[1]["extra"][0]["color"] == "black"   # not white on the page


@pytest.mark.mc
def test_the_server_keeps_the_color_of_the_heading(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    cmd, = replay.Replay(Fake(), data(TIMELINE)).timeline_commands(1_500_000)
    item = cmd[len("give @a "):]
    with run.Game(shutil.copytree(tiny_world[0], tmp_path / "W")) as game:
        game.command("forceload add 0 0")
        game.command("setblock 1 250 1 chest")
        out = game.command(f"item replace block 1 250 1 container.0 with {item}")
        path = 'Items[0].components."minecraft:written_book_content".pages[{}].raw.extra[{}]'
        heads = [game.command(f"data get block 1 250 1 {path.format(i, 0)}") for i in (1, 2)]   # page 0: "Players" (#4670)
        line = game.command(f"data get block 1 250 1 {path.format(1, 1)}")
    assert "Incorrect" not in out and "<--[HERE]" not in out, out
    assert 'color: "blue"' in heads[0] and "■ Player 1 (Britons)" in heads[0], heads   # the reply of RCON is short
    assert 'color: "gold"' in heads[1] and "■ Player 2 (Aztecs)" in heads[1], heads
    assert "Feudal Age" in line and "color" not in line, line
