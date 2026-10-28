"""The flare column of the live replay for the whole flare time (#2506, found by the check #2410): Replay.run sends a
burst of each live flare at least once per game second, also when no unit walks."""
from test_replay import Fake, data

from game import flare, replay


def bursts(speed):
    """The game times (s) of the column bursts of a flare at 1 s, with a chat line at 20 s and nothing between."""
    timeline = [{"time": 1000, "player": 1, "kind": "flare", "tile": [2.0, 2.0]},
                {"time": 20000, "player": 1, "kind": "chat", "text": "later"}]
    now, game = [0.0], Fake()

    def sleep(s):
        now[0] += s
    column = flare.particles(8, 70, 8, "@a", replay.FIREWORK_COLORS["blue"])
    sent = []
    game.command = lambda c: sent.append((now[0] * speed, c)) or ""
    replay.Replay(game, data(timeline)).run(speed, clock=lambda: now[0], sleep=sleep, log=None)
    return [t for t, c in sent if c == column]


def test_the_column_has_a_burst_in_each_second_of_the_flare_time():
    for speed in (1.0, 4.0):
        times = bursts(speed)
        assert all(any(s <= t < s + 1 for t in times) for s in range(1, 1 + flare.SECONDS)), (speed, times)
        assert max(times) < 1 + flare.SECONDS                         # no burst after the flare time
