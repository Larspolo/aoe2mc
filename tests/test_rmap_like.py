"""A DE object that object_kinds has not (the key "like" of data/rmap.jsonl, rmap.LIKE): create_object places the
object of its "like" (#4714)."""
import numpy as np

import rmap


def test_a_like_object_places_its_object_with_no_warning():
    for word, like in rmap.LIKE.items():
        warns = []
        out = rmap.objects([("create_object", [word], {})], {word: 99999}, np.zeros((20, 20), int), [],
                           np.random.default_rng(1), warns.append)
        assert [o["name"] for o in out] == [like] and warns == [], word
