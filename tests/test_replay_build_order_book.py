"""Live replay: each viewer gets a written book "Build order" at the end, the build order of each player on its own page
(#4048, item 2 of #4046)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_timeline_book import PREFIX, TIMELINE, book  # noqa: E402


def test_the_build_order_book_has_one_page_per_player_in_time_order():
    cmds = replay.Replay(Fake(), data(TIMELINE)).build_order_commands(1_500_000)
    assert len(cmds) == 1 and cmds[0].startswith(PREFIX)
    assert book(cmds) == {"title": "Build order", "author": "aoe2mc", "pages": [
        "■ Player 1 (Britons)\n\n10:20 Feudal Age\n11:40 Scout Cavalry\n21:05 Castle Age\n21:40 Castle",
        "■ Player 2 (Aztecs)\n\n01:40 Militia"]}


def test_a_long_build_order_stays_within_one_rcon_command():
    steps = [{"time": 1000 * i, "player": 1 + i % 2, "kind": "research", "technology": f"Tech {i}"} for i in range(160)]
    cmds = replay.Replay(Fake(), data(steps)).build_order_commands(10**9)
    assert len(cmds) == 1 and len(cmds[0].encode()) <= replay.RCON_MAX
    assert book(cmds)["pages"][0].startswith("■ Player 1") and "Tech 0" in book(cmds)["pages"][0]
