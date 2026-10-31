"""#5380: an if and a start_random each close their own kind, so an end_random inside an open if (Valley) does not
close the if, and a later else has its start."""
import numpy as np

import rmap


def words(text, defined=()):
    return rmap.expand(rmap.tokens(text), np.random.default_rng(1), set(defined), {}, [])


def test_an_end_random_in_an_open_if_closes_its_random_block():
    text = "start_random percent_chance 100 if A x end_random y else z endif"
    assert words(text, {"A"}) == ["x", "y"]
    assert words(text) == ["z"]

