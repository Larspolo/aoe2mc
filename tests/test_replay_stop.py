"""Live replay: the replay ends at the time of its last event, also when units still walk (#978). Fake RCON."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_walk import VIL  # noqa: E402


def play(timeline, **kw):
    d = data(timeline, n=160)
    d["objects"].append(VIL)
    now, game = [0.0], Fake()

    def sleep(s):
        now[0] += s
    r = replay.Replay(game, d, ai=True)
    r.run(4.0, clock=lambda: now[0], sleep=sleep, log=None, bar=True, **kw)
    return r, game.sent, now[0]


def seconds(name):
    m, s = re.search(r"(\d+):(\d\d)", name).groups()
    return int(m) * 60 + int(s)


def test_the_end_comes_at_the_last_event_while_a_unit_walks():
    tl = [dict(time=0, player=1, kind="move", objects=[7], tile=[35.5, 10.5], names=["VILLAGER_MALE"]),
          dict(time=10_000, player=1, kind="chat", text="gg")]
    r, sent, real = play(tl)
    names = [c.split(" name ")[1] for c in sent if c.startswith("bossbar") and " name " in c]
    assert max(map(seconds, names)) == 10 and names[-1] == '{"text": "End 00:10"}'
    assert "title @a title " + json.dumps(replay.say("replay_ended")) in sent
    assert real < 10 / 4 + 0.1                                     # it does not wait for the walk
    assert len([c for c in sent if c.startswith("aoe moveto")]) == 1    # the second leg never starts


def test_finish_plays_the_walk_to_its_end():
    tl = [dict(time=0, player=1, kind="move", objects=[7], tile=[35.5, 10.5], names=["VILLAGER_MALE"])]
    r, sent, _ = play(tl, finish=True)
    assert not r.moving and r.units[7].pos == (142.5, 70.0, 42.5)


def test_a_queue_spawns_no_unit_after_the_last_event():
    """The sample record queued units that the game made after 44:22: the clock counted on to 94:27 for them."""
    tl = [dict(time=0, player=1, kind="queue", type=83, objects=[5], name="VILLAGER_MALE", amount=3),   # 25, 50, 75 s
          dict(time=30_000, player=1, kind="chat", text="gg")]
    r, sent, real = play(tl)
    assert len(r.spawns()) == 3
    names = [c.split(" name ")[1] for c in sent if c.startswith("bossbar") and " name " in c]
    assert max(map(seconds, names)) == 30 and real < 30 / 4 + 0.1
