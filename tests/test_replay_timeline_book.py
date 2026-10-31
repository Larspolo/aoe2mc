"""Live replay: each viewer gets a written book "Timeline" at the end, one page per player with its age-ups, first
military unit, first castle and resign in time order (#1068)."""
import json
import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import lang  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

import aoe2mc  # noqa: E402

PREFIX = "give @a minecraft:written_book[minecraft:written_book_content="
TIMELINE = [{"time": 0, "player": 1, "kind": "queue", "type": 83, "objects": [5], "name": "VILLAGER_MALE"},
            {"time": 100_000, "player": 2, "kind": "queue", "type": 74, "objects": [6], "name": "MILITIA", "amount": 2},
            {"time": 620_620, "player": 1, "kind": "age", "age": "FEUDAL_AGE"},
            {"time": 700_000, "player": 1, "kind": "queue", "type": 448, "objects": [7], "name": "SCOUT_CAVALRY"},
            {"time": 1_265_000, "player": 1, "kind": "age", "age": "CASTLE_AGE"},
            {"time": 1_300_000, "player": 1, "kind": "build", "type": 82, "tile": [8.0, 8.0], "objects": [9]},
            {"time": 1_400_000, "player": 1, "kind": "build", "type": 82, "tile": [20.0, 8.0], "objects": [9]},
            {"time": 1_500_000, "player": 2, "kind": "resign"},
            {"time": 1_500_000, "player": 1, "kind": "chat", "text": "gg"}]
SCOUT, MILITIA = (replay.mmss(t + aoe2mc.train_ms(n)) for t, n in ((700_000, "SCOUT_CAVALRY"), (100_000, "MILITIA")))
PAGES = [f"■ Player 1 (Britons)\n\n10:20 Feudal Age\n{SCOUT} 1st military: Scout Cavalry\n21:05 Castle Age\n21:40 Castle",
         f"■ Player 2 (Aztecs)\n\n{MILITIA} 1st military: Militia\n25:00 Resigns"]   # at the end of the training


def text(page):
    """The plain text of a page component (the heading has a color, #1643)."""
    return lang.plain(page)                                          # the lines are translate texts (#5390)


def raw_book(cmds):
    """The book of the commands: one `give`, or an `item replace` and `item modify` appends (#5390)."""
    assert cmds[0].endswith("]") and (len(cmds) == 1) == cmds[0].startswith(PREFIX)
    b = json.loads(cmds[0].split("written_book_content=", 1)[1][:-1])
    for c in cmds[1:]:
        b["pages"] += json.loads("[" + c.split("pages:[", 1)[1][:-2] + "]")
    return b


def book(cmds):
    b = raw_book(cmds)
    return {**b, "pages": [text(p) for p in b["pages"][1:]]}          # after the players page (#4670)


def test_the_book_has_one_page_per_player_with_its_events_in_time_order():
    r = replay.Replay(Fake(), data(TIMELINE))
    assert book(r.timeline_commands(1_500_000)) == {"title": "Timeline", "author": "aoe2mc", "pages": PAGES}


def test_the_end_of_the_replay_gives_the_book_also_after_a_jump():
    now, game = [0.0], Fake()

    def sleep(s):
        now[0] += s
    replay.Replay(game, data(TIMELINE)).run(speed=8, clock=lambda: now[0], sleep=sleep, log=None, bar=True,
                                             to=1_450_000)
    timeline = PREFIX + '{"title":"Timeline"'                    # the book "Build order" comes too (#4048)
    assert book([c for c in game.sent if c.startswith(timeline)])["pages"] == PAGES
    assert game.sent.index(next(c for c in game.sent if c.startswith(timeline))) > \
        game.sent.index(next(c for c in game.sent if "aoe2mc.replay.replay_ended" in c))


def test_a_long_list_goes_on_to_the_next_page_and_the_command_stays_short():
    ages = [{"time": 60_000 * i, "player": 1, "kind": "age", "age": "FEUDAL_AGE"} for i in range(1, 15)]
    pages = book(replay.Replay(Fake(), data(ages)).timeline_commands(10**9))["pages"]
    assert pages[0].count("Feudal Age") == 11 and pages[1].count("Feudal Age") == 3 and len(pages) == 2   # 2 heading lines
    many = [{"time": 1000 * i, "player": 1 + i % 8, "kind": "age", "age": "IMPERIAL_AGE"} for i in range(400)]
    cmds = replay.Replay(Fake(), data(many)).timeline_commands(10**9)
    assert all(len(c.encode()) <= replay.RCON_MAX for c in cmds) and len(cmds) >= 2   # more commands (#5390)


def test_no_events_no_book():
    assert replay.Replay(Fake(), data([{"time": 0, "player": 1, "kind": "chat", "text": "hi"}])).timeline_commands(0) == []


@pytest.mark.mc
def test_the_give_command_passes_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    cmds = replay.Replay(Fake(), data(TIMELINE)).timeline_commands(1_500_000)
    with run.Game(shutil.copytree(tiny_world[0], tmp_path / "W")) as game:
        outs = [game.command(c) for c in cmds]
    assert not [o for o in outs if "Unknown" in o or "Incorrect" in o or "Invalid" in o or "<--[HERE]" in o], outs
