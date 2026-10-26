"""Recorded games of other game versions (#376): the mgz header parser reads the games that the mgz model cannot."""
import os
import shutil
from collections import Counter

import numpy as np
import pytest

import aoe2mc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HD = os.path.join(ROOT, "samples", "hd-4.6.aoe2record")
DE = os.path.join(ROOT, "samples", "de-64.3.aoe2record")
pytest.importorskip("mgz.model")


def test_hd_record_start_state():
    size, terrain, elevation, _, _, objects, players = aoe2mc.read_record(HD)
    assert size == 120 and terrain.shape == elevation.shape == (120, 120) and elevation.max() == 6
    assert players[1]["civ"] == "SARACENS" and players[1]["arch"] == "middle_eastern" and players[1]["color"] == "blue"
    assert players[2]["civ"] == "BRITONS" and players[2]["view"] == (35.0, 98.0)
    names = Counter(o["name"] for o in objects)
    assert names["TREE_SNOW_PINE"] > 2000          # the GAIA trees that the mgz header parser skips by default
    assert names["TOWN_CENTER"] == 2 and names["GOLD_MINE"] == 45 and not names.keys() & {"UNKNOWN_618"}
    tcs = {o["player"]: (o["x"], o["y"]) for o in objects if o["name"] == "TOWN_CENTER"}
    assert tcs == {1: players[1]["view"], 2: players[2]["view"]}
    assert aoe2mc.read_timeline(HD) is None        # no commands: only the start state


@pytest.mark.slow                                  # 8 s: FullSummary reads the whole DE body
def test_old_reader_matches_model_on_de():
    """The header parser and the mgz model give the same map and players for a DE game (tile order x, y)."""
    size, terrain, elevation, _, _, _, players = aoe2mc.read_record(DE)
    s2, t2, e2, _, _, _, p2 = aoe2mc.read_old_record(DE, None)
    assert s2 == size and np.array_equal(t2, terrain) and np.array_equal(e2, elevation)
    assert {k: (p["civ"], p["color"]) for k, p in p2.items()} == {k: (p["civ"], p["color"]) for k, p in players.items()}


def test_other_extensions_and_clear_error(tmp_path):
    mgz = tmp_path / "game.mgz"
    shutil.copy(HD, mgz)
    assert aoe2mc.read_map(str(mgz))[0] == 120
    bad = tmp_path / "bad.mgx"
    bad.write_bytes(open(HD, "rb").read()[:40000])
    with pytest.raises(SystemExit, match="cannot read this recorded game"):
        aoe2mc.read_map(str(bad))


def test_at_needs_commands(tmp_path):
    with pytest.raises(aoe2mc.OptionError, match="only its start state"):
        aoe2mc.convert(HD, str(tmp_path / "w"), at=60000)
