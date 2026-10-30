"""An RmsError of a stray endif names the words before it (#4707): the survey row shows the place of the error (Karsts, #4695)."""
import numpy as np
import pytest

import rmap


def test_a_stray_endif_names_the_words_before_it():
    with pytest.raises(rmap.RmsError) as e:
        rmap.expand(rmap.tokens("a b endif"), np.random.default_rng(0), set(), {}, [])
    assert str(e.value).startswith("endif without its start")
    assert "a b" in str(e.value)
