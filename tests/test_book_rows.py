"""book_pages counts an empty line as one row: the Economy book of the replay lost its last line (#4552)."""
import os
import sys
import textwrap

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

ECO = ["food 11", "wood 11", "gold 0", "stone 0", "build 0", "idle 0", "Spent:", "Eco 1175", "Mil 0", "Tech 50",
       "Build 656"]


def rows(page):
    text = "".join(x["text"] for x in page.get("extra", [])) or page["text"]
    return sum(max(1, len(textwrap.wrap(t, replay.BOOK_COLS))) for t in text.split("\n"))


def book(lines):
    r = replay.Replay(Fake(), data([]))
    r.player = lambda p: ("Player 1 (Byzantines)", "red")            # a two-row heading
    return r.book_pages({1: lines})


def test_an_empty_line_takes_a_row():
    pages = book([f"line {i}" for i in range(10)] + ["", "last"])     # 2 + 1 + 12 rows: one more than a page
    assert len(pages) == 2 and all(rows(pg) <= replay.BOOK_ROWS for pg in pages)
    assert pages[1]["text"] == "last"


def test_the_economy_page_of_a_player_fits_one_page():
    pages = book(ECO)
    assert len(pages) == 1 and rows(pages[0]) <= replay.BOOK_ROWS and pages[0]["extra"][1]["text"].endswith("Build 656")
