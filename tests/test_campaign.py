"""Campaign files (.aoe2campaign): one world per scenario (#200)."""
import contextlib
import io
import struct

import pytest

import aoe2mc
import scenarios


def de_string(text):
    raw = text.encode()
    return b"\x60\x0a" + struct.pack("<H", len(raw)) + raw


def campaign(path, scenario_files, name="test campaign"):
    """An .aoe2campaign with the layout of docs/campaign-formats.md (version 2.00, no dependencies)."""
    datas = [open(f, "rb").read() for f in scenario_files]
    titles = [f"S{i}.aoe2scenario" for i in range(1, len(datas) + 1)]
    head = b"2.00" + struct.pack("<I", 0) + name.encode().ljust(256, b"\0") + struct.pack("<I", len(datas))
    table_size = sum(8 + 2 * len(de_string(t)) for t in titles)
    off, table = len(head) + table_size, b""
    for t, d in zip(titles, datas):
        table += struct.pack("<II", len(d), off) + de_string(t) * 2
        off += len(d)
    path.write_bytes(head + table + b"".join(datas))
    return path


@pytest.fixture(scope="module")
def camp(tmp_path_factory):
    d = tmp_path_factory.mktemp("camp")
    s1 = scenarios.tiny(str(d / "a.aoe2scenario"))
    s2 = scenarios.save(scenarios.new_scenario(8), str(d / "b.aoe2scenario"))
    return campaign(d / "c.aoe2campaign", [s1, s2])


def run(*args):
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.main([str(a) for a in args])


def test_read_campaign(camp):
    name, entries = aoe2mc.read_campaign(camp)
    assert name == "test campaign"
    assert [t for t, _ in entries] == ["S1.aoe2scenario", "S2.aoe2scenario"]
    assert all(data[:2] == b"1." for _, data in entries)        # each part is a scenario file


def test_one_world_per_scenario(camp, tmp_path):
    run(camp, tmp_path / "out")
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["1 S1", "2 S2"]
    assert all((tmp_path / "out" / w / "level.dat").exists() for w in ("1 S1", "2 S2"))


def test_only_one_scenario(camp, tmp_path):
    run(camp, tmp_path / "out", "--scenario", 2)
    assert [p.name for p in (tmp_path / "out").iterdir()] == ["2 S2"]


def error(*args):
    err = io.StringIO()
    with pytest.raises(SystemExit) as e, contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.main([str(a) for a in args])
    assert e.value.code == 2
    return err.getvalue()


@pytest.mark.parametrize("cut, msg", [(100, "the file ends in the header"), (None, "ends after the end of the file")])
def test_broken_campaign(camp, tmp_path, cut, msg):
    b = camp.read_bytes()
    bad = tmp_path / "bad.aoe2campaign"
    bad.write_bytes(b[:cut] if cut else b[:-10])
    assert msg in error(bad, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_wrong_version_and_options(camp, tmp_path):
    old = tmp_path / "old.aoe2campaign"
    old.write_bytes(b"1.00" + camp.read_bytes()[4:])
    assert "only .aoe2campaign files (AoE2 DE)" in error(old, tmp_path / "out")
    assert "has 2 scenarios" in error(camp, tmp_path / "out", "--scenario", 3)
    assert "--scenario needs a .aoe2campaign file" in error("in.aoe2scenario", tmp_path / "out", "--scenario", 1)
