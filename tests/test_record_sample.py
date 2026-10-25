"""The recorded game in samples/ (#134) is there with its license note, and `mgz` reads it (skip without `mgz`)."""
import os

import pytest

REC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "de-64.3.aoe2record")


def test_record_sample_has_license_note():
    assert os.path.getsize(REC) > 1_000_000
    assert "MIT License" in open(REC + ".LICENSE.txt").read()


def test_record_sample_parses():
    model = pytest.importorskip("mgz.model")
    with open(REC, "rb") as f:
        match = model.parse_match(f)
    assert "Acropolis" in match.map.name and match.map.size == "Tiny"
    assert [p.civilization for p in match.players] == ["Byzantines", "Aztecs"]
    assert len(match.map.tiles) == 120 * 120
