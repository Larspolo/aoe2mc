"""A percent_chance with a math expression or a #const (#5171)."""
import numpy as np

import rmap


def expand(text, seed=0):
    return rmap.expand(rmap.tokens(text), np.random.default_rng(seed), set(), {}, [])


SCRIPT = "#const A 45 start_random percent_chance (A + 5) x percent_chance A y end_random z"


def test_math_percent_chance():
    out = expand(SCRIPT)
    assert out[-1] == "z" and out[:-1] in ([], ["x"], ["y"])


def test_same_seed_same_branch():
    assert all(expand(SCRIPT, s) == expand(SCRIPT, s) for s in range(10))
    assert {"x", "y"} <= {expand(SCRIPT, s)[0] for s in range(40)}


def test_plain_number_still_works():
    assert expand("start_random percent_chance 100 x end_random") == ["x"]
