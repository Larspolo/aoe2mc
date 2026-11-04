"""Bot.home decides the sources of the base with arrays (#5736): the same answer as the plain distance check, also for
the far sources when the base has none left."""
import math
import types

import bot
import numpy as np


def plain(sources, own, foe, T, far):
    d = lambda t, ps: min(math.dist(((t[0] + 0.5) * T, (t[1] + 0.5) * T), p) for p in ps)  # noqa: E731
    kept = {t: k for t, k in sources.items() if d(t, own) <= d(t, foe)}
    if not far or any(k > 0 for k in kept.values()):
        return kept
    half = max(min(math.dist(p, q) for q in foe) for p in own) / 2
    beyond = {t: k for t, k in sources.items() if d(t, foe) >= half}
    return beyond if any(k > 0 for k in beyond.values()) else {t: k for t, k in sources.items() if k > 0}


def home(sources, own, foe, T=4, far=False):
    b = object.__new__(bot.Bot)
    b.foe, b.share, b.sides = 2, None, (None, {})
    objects = [{"kind": "building", "player": 2, "footprint": [x, z, x, z]} for x, z in foe]
    b.g = types.SimpleNamespace(map=types.SimpleNamespace(T=T, drops={"wood": [[c] for c in own]}),
                                data={"objects": objects})
    return b.home(sources, far=far)


def test_same_answer_as_the_plain_check():
    rng = np.random.default_rng(5736)
    for _ in range(200):
        sources = {tuple(int(v) for v in rng.integers(0, 60, 2)): int(rng.integers(0, 3)) for _ in range(rng.integers(1, 30))}
        own = [tuple(float(v) for v in rng.integers(0, 240, 2)) for _ in range(rng.integers(1, 5))]
        foe = [tuple(float(v) for v in rng.integers(0, 240, 2)) for _ in range(rng.integers(1, 5))]
        for far in (False, True):
            assert home(sources, own, foe, far=far) == plain(sources, sorted(own), foe, 4, far)
