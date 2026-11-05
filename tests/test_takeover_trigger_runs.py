"""The bot step after a takeover is fast enough for the game loop (#5736): Bot.remote checks the pairs of sources and
drop-site cells in one array operation, with the same answer as the plain distance check."""
import math
import types

import bot
import numpy as np


def plain(full, drops, T):
    return all(math.dist(((t[0] + 0.5) * T, (t[1] + 0.5) * T), c) > bot.FAR * T for t in full for c in drops)


def remote(full, drops, T=4):
    b = object.__new__(bot.Bot)
    b.g = types.SimpleNamespace(map=types.SimpleNamespace(T=T, drops={"wood": [drops]}))
    b.sources = lambda res: {t: 10 for t in full}
    return b.remote("LUMBER_CAMP" if "LUMBER_CAMP" in bot.NEAR else next(k for k, v in bot.NEAR.items() if v == "wood"))


def test_same_answer_as_the_plain_check():
    rng = np.random.default_rng(5736)
    for _ in range(200):
        full = [tuple(int(v) for v in rng.integers(0, 60, 2)) for _ in range(rng.integers(1, 30))]
        drops = [tuple(float(v) for v in rng.integers(0, 240, 2)) for _ in range(rng.integers(1, 20))]
        assert remote(full, drops) == plain(full, drops, 4)


def test_no_drop_site_is_remote():
    assert remote([(3, 3)], []) is True


def test_a_slow_step_stops_the_clock():
    """A step that takes longer than its tick stops the game clock of the person and the bots for the extra time: the
    clock does not go faster than the work of the steps (train.tick, the gather timers)."""
    import gather
    import recap
    now = [0.0]
    clock = lambda: now[0]                                             # noqa: E731
    me = types.SimpleNamespace(clock=clock, t0=0.0, speed=4.0, bots=[])
    foe = types.SimpleNamespace(g=types.SimpleNamespace(clock=clock, t0=0.0, speed=4.0))
    me.bots = [foe, types.SimpleNamespace()]                           # a bot without its own Gather (a driver)
    now[0] = 1.5                                                       # one step of 1.5 s, tick 0.25 at speed 4
    gather.lag(me, now[0] - 0.25 / 4)
    assert recap.game_time(me) == recap.game_time(foe.g) == 0.25 * gather.NORMAL     # one tick of work
    gather.lag(me, -0.01)                                              # a fast step changes nothing
    assert me.t0 == foe.g.t0 == 1.5 - 0.0625
