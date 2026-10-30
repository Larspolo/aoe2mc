"""Slow: convert a scenario with every object type of the parser and check the complete world.

Run with:  pytest -m slow
"""
import contextlib
import io

import mcvalid
import pytest
import scenarios
import world_reader
from entities import entity_ids

import aoe2mc


@pytest.mark.slow
def test_gallery_world(tmp_path):
    src = scenarios.gallery(str(tmp_path / "gallery.aoe2scenario"))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        aoe2mc.convert(src, str(tmp_path / "GalleryWorld"))
    w = world_reader.World(str(tmp_path / "GalleryWorld"))
    assert mcvalid.invalid_states(w.palette(), aoe2mc.VERSION_NAME) == {}
    for e in w.entities(flat=False):
        for i in entity_ids(e):
            assert mcvalid.entity_error(i, aoe2mc.VERSION_NAME) is None, i
