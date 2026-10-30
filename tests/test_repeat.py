"""convert() must give the same world when it runs more than once in one process."""
import contextlib
import io

import scenarios
import world_reader

import aoe2mc


def run(src, out, **kw):
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        aoe2mc.convert(src, out, **kw)
    return world_reader.World(out), [ln for ln in log.getvalue().splitlines() if "units in a block" in ln]


def test_two_conversions_give_the_same_world(tmp_path):
    src = scenarios.tiny(str(tmp_path / "tiny.aoe2scenario"))
    aoe2mc.MOVED["(left over)"] += 5                              # a count of an earlier conversion
    w1, moved1 = run(src, str(tmp_path / "A"))
    _, _ = run(src, str(tmp_path / "B"), barriers=False)          # an earlier conversion with other options
    w2, moved2 = run(src, str(tmp_path / "C"))
    assert moved1 == moved2 == ["  units in a block (moved up): 0"]
    c1, c2 = w1.chunks(), w2.chunks()
    assert c1.keys() == c2.keys()
    for k in c1:
        assert c1[k] == c2[k], k
    e1, e2 = w1.entities(), w2.entities()
    assert len(e1) == len(e2) > 0
    assert e1 == e2


def test_convert_without_barriers(tmp_path):
    src = scenarios.tiny(str(tmp_path / "tiny.aoe2scenario"))
    w, _ = run(src, str(tmp_path / "A"), barriers=False)
    assert not any("barrier" in s for s in w.palette())
    w, _ = run(src, str(tmp_path / "B"))
    assert any("barrier" in s for s in w.palette())


def test_unknown_object_ids_are_reported(tmp_path):
    scn = scenarios.new_scenario(16)
    for x in (2.5, 4.5):
        scn.unit_manager.add_unit(scenarios.PlayerId.GAIA, 9999, x=x, y=2.5)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, 9998, x=8.5, y=8.5)
    src = scenarios.save(scn, str(tmp_path / "unknown.aoe2scenario"))
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        aoe2mc.convert(src, str(tmp_path / "W"))
    assert "  unknown object IDs (skipped): 9998 ×1, 9999 ×2" in log.getvalue().splitlines()
