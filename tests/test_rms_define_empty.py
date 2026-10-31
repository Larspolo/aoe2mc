"""A #define line with no label defines nothing (Valley, #5422): the next line is read as usual, so its `if` is no label."""
import numpy as np

import rmap


def expand(text, defined=()):
    return rmap.expand(rmap.tokens(text), np.random.default_rng(0), set(defined), {}, [])


def test_a_define_alone_on_its_line_defines_nothing():
    assert expand("#define\nif LABEL\na\nelse\nb\nendif\n") == ["b"]


def test_a_define_alone_does_not_hide_the_words_after_it():
    assert expand("x\n#define\ny z") == ["x", "y", "z"]
