"""A record with no start position of a player (Steppe, ranked 2026-10-29) reads with no view (#4559)."""
from types import SimpleNamespace as N

import pytest

import aoe2mc

pytest.importorskip("mgz.model")


def test_record_position_none_gives_no_view(monkeypatch, tmp_path):
    p = N(number=1, civilization="Byzantines", color_id=0, position=N(x=None, y=None), objects=[])
    match = N(map=N(dimension=2, tiles=[]), teams=[[p]], players=[p], gaia=[])
    monkeypatch.setattr("mgz.model.parse_match", lambda f: match)
    path = tmp_path / "r.aoe2record"
    path.write_bytes(b"")
    assert aoe2mc.read_record(str(path))[6][1]["view"] is None
