"""A running replay takes the new events of a live record (#4662, epic #4660): a timeline in two parts sends the same
commands as the same timeline in one part, and the replay waits at its last event until the record is complete."""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay  # noqa: E402
from test_replay import build, data  # noqa: E402
from test_replay_control import Clock, chats  # noqa: E402

TIMELINE = chats(1000, 4000) + [build("HOUSE", (8.0, 8.0), 5000)] + chats(9000) + \
    [build("HOUSE", (12.0, 8.0), 12000)] + chats(15000, 20000)


def play(more=None, timeline=TIMELINE, bar=False):
    game = Clock()
    r = replay.Replay(game, data(copy.deepcopy(timeline)))
    r.run(clock=lambda: game.now, sleep=game.sleep, log=None, more=more, bar=bar)
    return game, r


def parts(cut, when, timeline=TIMELINE):
    """more() of a record that has the events before `cut` (ms), and all of them from real time `when` (s)."""
    game = []
    sent = []

    def more():
        if game[0].now < when:
            return [], False
        out = [] if sent else copy.deepcopy([e for e in timeline if e["time"] >= cut])
        sent.append(1)
        return out, True
    return game, more


def test_two_parts_send_the_commands_of_one_part():
    whole, _ = play()
    holder, more = parts(9000, 3.0)
    game = Clock()
    holder.append(game)
    r = replay.Replay(game, data(copy.deepcopy([e for e in TIMELINE if e["time"] < 9000])))
    r.run(clock=lambda: game.now, sleep=game.sleep, log=None, more=more, poll=lambda control: None)
    assert game.sent == whole.sent
    assert game.at == whole.at                       # each chat at its game time: the new part came before it
    assert len(r.data["timeline"]) == len(TIMELINE)


def test_the_replay_waits_at_its_end_for_the_next_part():
    holder, more = parts(9000, 30.0)
    game = Clock()
    holder.append(game)
    r = replay.Replay(game, data(copy.deepcopy([e for e in TIMELINE if e["time"] < 9000])))
    r.run(clock=lambda: game.now, sleep=game.sleep, log=None, more=more)
    assert game.at["t4000"] == 4.0
    assert game.at["t9000"] >= 30.0                  # it waited at 0:05 until the part came at 30 s
    assert game.at["t20000"] - game.at["t9000"] == 11.0   # then on at game speed from the end of the old part
    assert r.ended == 20000


def test_a_complete_record_ends_the_wait():
    calls = []

    def more():
        calls.append(1)
        return [], len(calls) >= 3
    game, r = play(more, timeline=chats(1000), bar=True)
    assert len(calls) == 3 and game.at["t1000"] == 1.0
    assert any(c.startswith("tellraw") and "Summary" in c for c in game.sent)   # the end of the replay as before


def test_no_source_plays_as_before():
    game, r = play()
    assert game.at["t20000"] == 20.0 and r.ended == 20000
