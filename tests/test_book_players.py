"""Each summary book of the live replay starts with a page of the players, as the AoE2 DE loading screen (#4670)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import lang  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

PLAYERS = {"1": {"name": "Ann", "civ": "BRITONS", "color": "blue", "team": 1, "rating": 1234, "rating_now": True},
           "2": {"name": "Bob", "civ": "AZTECS", "color": "red", "team": 2},
           "3": {"name": "Cid", "civ": "FRANKS", "color": "white", "team": 1},
           "4": {"name": "Dan", "civ": "MAYANS", "color": "green", "team": 2}}


def game():
    d = data([])
    d["players"] = json.loads(json.dumps(PLAYERS))
    return replay.Replay(Fake(), d)


def test_the_first_page_has_a_line_per_player_in_panel_order():
    r = game()
    lines = {1: ["a", "b"], 2: ["c"]}
    pages = r.book_pages(lines, players=True)
    extra = pages[0]["extra"]
    assert [lang.plain(e).lstrip("\n") for e in extra] == [
        f"Team {r.team(p)} · {r.player(p)[0]}" + (" · 1234 now" if p == 1 else "") for p in r.ranked([1, 2, 3, 4])]
    assert [e["color"] for e in extra] == [c if c != "white" else "black"
                                           for c in (r.player(p)[1] for p in r.ranked([1, 2, 3, 4]))]
    assert len(pages) == 3 and pages[1]["extra"][1]["text"] == "\n\na\nb" and pages[2]["extra"][1]["text"] == "\n\nc"


def test_a_long_book_keeps_the_players_page():
    r = game()
    cmd = r.book_command("Timeline", {1: ["x" * 18] * 3000})[0]
    assert len(cmd.encode()) <= replay.RCON_MAX
    book = json.loads(cmd.split("written_book_content=", 1)[1][:-1])
    assert book["pages"][0] == r.players_page()
