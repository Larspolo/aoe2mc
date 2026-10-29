"""generate() collects its object parts one per line (#4014): the same seed still gives the same map."""
import contextlib
import io

import pytest

import rmap


@pytest.mark.parametrize("kind", sorted(rmap.GENERATORS))
def test_same_map_for_the_same_seed(kind):
    with contextlib.redirect_stderr(io.StringIO()):
        a, b = rmap.random_map(kind, 1), rmap.random_map(kind, 1)
    assert a == b


def test_sections_one_per_line():
    src = open(rmap.__file__).read()
    for s in rmap.SECTIONS:
        assert f'\n    "{s}",\n' in src
