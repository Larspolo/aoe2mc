"""Records of save version 68.9 (#3686): aoe2mc.new_saves() adds the new DE header strings to mgz."""
import os

import pytest

import aoe2mc

RECORD = os.environ.get("AOE2MC_RECORD_68")         # a 68.9 record: the test record of the owner is not in samples/ yet


def test_the_patch_adds_the_reads_of_new_saves_once():
    from mgz.fast import header
    assert 66.6 not in header.parse_de.__code__.co_consts or header.parse_de.new_saves
    aoe2mc.new_saves()
    assert header.parse_de.new_saves and 66.6 in header.parse_de.__code__.co_consts
    code = header.parse_de.__code__
    aoe2mc.new_saves()                                   # a second call changes nothing
    assert header.parse_de.__code__ is code


def test_the_old_records_still_parse():
    aoe2mc.new_saves()
    events = aoe2mc.read_timeline("samples/de-64.3.aoe2record")
    assert events and any(e["kind"] == "build" for e in events)


@pytest.mark.skipif(not RECORD, reason="set AOE2MC_RECORD_68 to a record of save version 68.9")
def test_a_68_9_record_parses():
    out = aoe2mc.read_record(RECORD)
    assert out
    events = aoe2mc.read_timeline(RECORD)
    assert events and {"build", "queue", "move"} <= {e["kind"] for e in events}
