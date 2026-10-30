"""A record that AoE2 DE still writes, cut at any byte, reads with no error (#4661): the events up to the cut."""
import os

import pytest

import aoe2mc

RECORD = "samples/de-63.0.aoe2record"    # the smallest sample with a timeline (hd-4.6 has none)


@pytest.mark.slow
def test_cut_body_gives_first_events(tmp_path):
    data = open(RECORD, "rb").read()
    full = aoe2mc.read_timeline(RECORD)
    objects = aoe2mc.read_record(RECORD)[5]
    for frac in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.99):
        p = os.path.join(tmp_path, "cut.aoe2record")
        with open(p, "wb") as f:
            f.write(data[:int(len(data) * frac)])
        events = aoe2mc.read_timeline(p)
        assert events and events == full[:len(events)], frac
        assert aoe2mc.read_record(p)[5] == objects, frac


def test_cut_header_gives_no_start(tmp_path):
    p = os.path.join(tmp_path, "cut.aoe2record")
    with open(RECORD, "rb") as f, open(p, "wb") as g:
        g.write(f.read(1000))
    assert aoe2mc.read_timeline(p) is None
    with pytest.raises(SystemExit, match="the record has no start yet"):
        aoe2mc.read_record(p)
