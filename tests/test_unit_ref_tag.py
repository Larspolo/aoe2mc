"""Each unit of a converted scenario has the tag aoe2mc.r<ID> of its reference ID, also a Gaia unit, so that the
triggers find one object (#2617). The objects of a record get no such tag."""
import contextlib
import io

import numpy as np

import aoe2mc
import units
import world_reader
from tools import scenarios


def tags(o):
    nbt = units.make_entity(dict(rotation=0.0, **o), {}, (0.5, 0.0, 0.5), np.random.default_rng(1))
    return {str(t) for t in units.top_entity(nbt).get("Tags", [])}


def test_scenario_unit_gets_its_reference_tag():
    assert tags(dict(name="KNIGHT", player=1, id=38, ref=7, ref_tag=True)) == {"aoe2mc.p1", "aoe2mc.t38", "aoe2mc.r7"}
    assert tags(dict(name="SHEEP", player=0, id=594, ref=7, ref_tag=True)) == {"aoe2mc.p0", "aoe2mc.t594", "aoe2mc.r7"}   # Gaia too


def test_no_reference_or_a_record_gives_no_tag():
    assert tags(dict(name="KNIGHT", player=1, id=38, ref=None, ref_tag=True)) == {"aoe2mc.p1", "aoe2mc.t38"}
    assert tags(dict(name="SHEEP", player=0, id=594)) == {"aoe2mc.p0", "aoe2mc.t594"}
    assert tags(dict(name="KNIGHT", player=1, id=38, ref=7)) == {"aoe2mc.p1", "aoe2mc.t38"}   # a record object ID


def test_converted_scenario_has_one_tag_per_reference(tmp_path):
    src = scenarios.triggers(str(tmp_path / "t.aoe2scenario"))
    objects = aoe2mc.read_scenario(src)[5]
    assert all(o["ref_tag"] for o in objects)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    refs = [t for e in world_reader.World(str(tmp_path / "W")).entities() for t in map(str, e.get("Tags", []))
            if t.startswith("aoe2mc.r")]
    assert refs and len(refs) == len(set(refs))
    sheep = {o["ref"] for o in objects if o["name"] == "SHEEP"}
    assert sheep and {f"aoe2mc.r{r}" for r in sheep} <= set(refs)                      # the Gaia sheep
