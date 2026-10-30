"""The actions per minute of two players of a recorded game, counted by mgz (#3842, part of #3762): the last minute
and the average of Replay.apm and Replay.mean_apm equal the own count of the actions in the record."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

import aoe2mc  # noqa: E402

REC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "de-64.3.aoe2record")
TIMES = (5 * 60000, 20 * 60000)


def own_times():
    """The times (ms) of the commands of players 1 and 2. The DE_QUEUE patch of read_timeline is needed: plain mgz
    gives such a command as ERROR (2 of them in the first 5 minutes), and the player did give it."""
    import mgz.fast as fast
    import mgz.model
    parse = fast.parse_action
    fast.parse_action = aoe2mc.de_queue(parse)
    aoe2mc.new_saves()
    try:
        with open(REC, "rb") as f, aoe2mc.own_selection():
            actions = mgz.model.parse_match(f).actions
    finally:
        fast.parse_action = parse
    ms = lambda a: int(round(a.timestamp.total_seconds() * 1000))   # noqa: E731
    return {p: sorted(ms(a) for a in actions if a.player and a.player.number == p and a.type.name != "ERROR")
            for p in (1, 2)}


def test_the_apm_of_two_players_equal_the_count_of_mgz():
    own = own_times()
    r = replay.Replay(Fake(), data(aoe2mc.read_timeline(REC), n=480))
    for p in (1, 2):
        for t in TIMES:
            last = sum(1 for x in own[p] if t - 60000 < x <= t)
            upto = sum(1 for x in own[p] if x <= t)
            assert r.apm(p, t) == last > 0
            assert r.mean_apm(p, t) == round(upto / (t / 60000))
