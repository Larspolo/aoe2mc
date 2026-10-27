"""Live replay on Paper: CLOSE ms after the start of a long leg, the replay reads the entity once more and sets its
walk speed again (#1293: after a turn on a leg a villager of de-64.3 stayed 5 to 11 blocks behind for 30 s). Fake RCON."""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import ai  # noqa: E402
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_catch_up import Entity  # noqa: E402
from test_replay_walk import VIL  # noqa: E402


def turn(at):
    """A villager at block x 122 walks east from 1 s, and at 9 s back west (a turn). Its entity stands at `at`.
    Returns the sent commands from the turn on."""
    tl = [dict(time=1000, player=1, kind="move", objects=[7], tile=[60.5, 10.5]),
          dict(time=9000, player=1, kind="move", objects=[7], tile=[2.5, 10.5])]
    d = data(tl, n=256)
    d["objects"] += [dict(VIL, tile=[30.5, 10.5])]
    now, game = [0.0], Entity(at=at)
    r = replay.Replay(game, d, ai=True)
    r.run(4.0, clock=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0] + s), log=None, finish=True)
    moves = [k for k, c in enumerate(game.sent) if (m := re.match(r"aoe moveto u1 (\S+) ", c)) and float(m[1]) < 120]
    return game.sent[moves[0] - 1:]


def test_a_villager_behind_after_a_turn_walks_faster_after_close_ms():
    """At the turn the entity (x 140) is nearer to the end of the new leg than the replay unit (x 147.6): the order
    sees no lag. 5 s later the replay unit is at x 131.6 and the entity 8.4 blocks behind it: the speed goes up."""
    sent = turn((140.5, 42.5))
    speeds = [c for c in sent if c.startswith("attribute u1 ")]
    assert speeds[0] == ai.speed_command("u1", "VILLAGER_MALE", 4, 4.0 * replay.PATH)        # the order at the turn
    assert speeds[1] == ai.speed_command("u1", "VILLAGER_MALE", 4, 4.0 * replay.CATCH_UP)    # the recheck
    k = sent.index(speeds[1])                                      # before the next leg: no new walk order
    assert sent[k - 1] == "data get entity u1 Pos" and not sent[k + 1].startswith("aoe moveto u1 ")


def test_a_walk_reads_the_entity_at_most_twice_per_leg():
    sent = turn(None)                                              # the entity stays at the start of each leg
    legs = [c for c in sent if c.startswith("aoe moveto u1 ")]
    reads = [c for c in sent if c == "data get entity u1 Pos"]
    assert 2 <= len(legs) and len(reads) <= 2 * len(legs)          # the order of a leg behind and its recheck
