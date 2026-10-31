"""#4706: a saved game of DE is one raw deflate stream with no header_length prefix. saved_match reads it as the
header of a record."""
import os

import pytest

import aoe2mc

SAMPLES = os.path.join(os.path.dirname(__file__), os.pardir, "samples")
RECORD = os.path.join(SAMPLES, "de-64.3.aoe2record")


def test_a_save_of_one_raw_deflate_stream_reads(tmp_path):
    data = open(RECORD, "rb").read()
    path = tmp_path / "raw.aoe2spgame"
    path.write_bytes(data[8:int.from_bytes(data[:4], "little")])   # the deflate block, no prefix
    match = aoe2mc.saved_match(str(path))
    assert len(match.players) == 2


def test_the_raw_sample_save_gets_past_the_header_block():
    path = os.path.join(SAMPLES, "aoe2mc-sample.aoe2spgame")
    if not os.path.exists(path):
        pytest.skip("no sample save")
    try:
        aoe2mc.saved_match(path)
    except SystemExit as e:             # mgz 1.8.51 cannot read save 68.9 yet (saved-games.md)
        assert "no header block" not in str(e)
