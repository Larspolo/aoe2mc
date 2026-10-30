"""A percent_chance inside an if inside a start_random (#4692): AoE2 DE keeps the if blocks and the random blocks
apart, so the percent_chance belongs to the random block under the if."""
import numpy as np
import pytest

import rmap
from test_rmap import SCRIPT, make

SIZED = """start_random
  if TINY_MAP
    percent_chance 40 A
  else
    percent_chance 60 B
  endif
end_random"""


def picks(text, defined=(), seeds=200):
    return [tuple(rmap.expand(rmap.tokens(text), np.random.default_rng(s), set(defined), {}, [])) for s in range(seeds)]


def test_a_percent_chance_in_an_if_uses_the_random_block_under_the_if():
    tiny, other = picks(SIZED, {"TINY_MAP"}), picks(SIZED)
    assert set(tiny) == {("A",), ()} and set(other) == {("B",), ()}
    assert 50 < tiny.count(("A",)) < 110 and 90 < other.count(("B",)) < 150


def test_an_if_before_the_first_percent_chance_reads_its_label():
    assert set(picks("start_random if X percent_chance 100 A endif end_random", {"X"})) == {("A",)}


def test_words_after_the_endif_stay_in_the_branch_of_the_last_percent_chance():
    assert set(picks("start_random if X percent_chance 100 A endif B end_random C", {"X"})) == {("A", "B", "C")}


def test_a_percent_chance_without_a_start_random_is_an_error():
    with pytest.raises(rmap.RmsError):
        picks("percent_chance 50 A", seeds=1)


def test_the_form_in_a_script_gives_a_map():
    d, _ = make(3, script="#define TINY_MAP\n" + SIZED.replace(" A", " #define LOTS") + "\n" + SCRIPT)
    assert d["terrain"]
