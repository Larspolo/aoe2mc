"""Campaign files: .aoe2campaign gives one world per scenario (#200), .cpx the old scenarios and the steps (#201)."""
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
    version, name, entries = aoe2mc.read_campaign(camp)
    assert (version, name) == (b"2.00", "test campaign")
    assert [t for t, _ in entries] == ["S1.aoe2scenario", "S2.aoe2scenario"]
    assert all(data[:2] == b"1." for _, data in entries)        # each part is a scenario file


def test_one_world_per_scenario(camp, tmp_path):
    run(camp, tmp_path / "out")
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["1 S1", "2 S2", "campaign.json"]
    assert all((tmp_path / "out" / w / "level.dat").exists() for w in ("1 S1", "2 S2"))


def test_only_one_scenario(camp, tmp_path):
    run(camp, tmp_path / "out", "--scenario", 2)
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["2 S2", "campaign.json"]


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
    other = tmp_path / "other.aoe2campaign"
    other.write_bytes(b"3.00" + camp.read_bytes()[4:])
    assert "is not 1.00 (.cpx, .cpn) or 2.00 (.aoe2campaign)" in error(other, tmp_path / "out")
    assert "has 2 scenarios" in error(camp, tmp_path / "out", "--scenario", 3)
    assert "--scenario needs a campaign file" in error("in.aoe2scenario", tmp_path / "out", "--scenario", 1)


def cpx(path, scenarios, name="Old campaign"):
    """A .cpx (version 1.00): fixed strings, 520-byte table entries. scenarios: [(file name, bytes)]."""
    head = b"1.00" + name.encode("cp1252").ljust(256, b"\0") + struct.pack("<I", len(scenarios))
    off, table = len(head) + 520 * len(scenarios), b""
    for fn, d in scenarios:
        stem = fn.rsplit(".", 1)[0].encode("cp1252")
        table += struct.pack("<ii", len(d), off) + stem.ljust(255, b"\0") + fn.encode("cp1252").ljust(255, b"\0") + b"\0\0"
        off += len(d)
    path.write_bytes(head + table + b"".join(d for _, d in scenarios))
    return path


OLD = [("Der Weg nach Sacsahuam\u00e1n.scx", b"1.21" + bytes(range(200))), ("Zwei.scx", b"1.21" + b"\x01" * 50)]


def test_cpx_writes_old_scenarios_and_steps(tmp_path):
    c = cpx(tmp_path / "old.cpx", OLD)
    assert aoe2mc.read_campaign(c) == (b"1.00", "Old campaign", OLD)
    err = io.StringIO()
    with pytest.raises(SystemExit) as e, contextlib.redirect_stdout(err):
        aoe2mc.main([str(c), str(tmp_path / "out")])
    msg = str(e.value.code)
    assert "old scenario format (.scx)" in msg and "1. Copy the files" in msg and "3. Convert" in msg
    assert (tmp_path / "out" / f"1 {OLD[0][0]}").read_bytes() == OLD[0][1]
    assert (tmp_path / "out" / "2 Zwei.scx").read_bytes() == OLD[1][1]


def test_cpx_one_scenario(tmp_path):
    with pytest.raises(SystemExit), contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.main([str(cpx(tmp_path / "old.cpx", OLD)), str(tmp_path / "out"), "--scenario", "2"])
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["2 Zwei.scx", "campaign.json"]


def scx_bytes(tmp_path, name, players):
    import numpy as np
    from test_scx import build
    t = np.zeros((16, 16), np.uint8)
    return open(build(tmp_path / name, t, np.zeros((16, 16), int), players, [(1, 8.5, 8.5, 83)]), "rb").read()


def test_cpx_converts_its_scx_scenarios(tmp_path):
    """The .scx scenarios of format 1.21 give one world each, without the DE editor steps (#347)."""
    a, b = scx_bytes(tmp_path, "a.scx", {1: (1, 0, (8, 8))}), scx_bytes(tmp_path, "b.scx", {1: (2, 1, (4, 4))})
    c = cpx(tmp_path / "old.cpx", [("Erste.scx", a), ("Zweite.scx", b)])
    run(c, tmp_path / "out")
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["1 Erste", "2 Zweite", "campaign.json"]
    assert (tmp_path / "out" / "2 Zweite" / "level.dat").exists()
    run(c, tmp_path / "one", "--scenario", "2")
    assert sorted(p.name for p in (tmp_path / "one").iterdir()) == ["2 Zweite", "campaign.json"]


def test_cpx_with_other_formats_converts_the_rest_and_gives_the_steps(tmp_path):
    a = scx_bytes(tmp_path, "a.scx", {1: (1, 0, (8, 8))})
    c = cpx(tmp_path / "old.cpx", [("Gut.scx", a), ("Alt.scx", b"1.18" + bytes(100)), ("Karte.scn", b"1.10" + bytes(9))])
    out = io.StringIO()
    with pytest.raises(SystemExit) as e, contextlib.redirect_stdout(out):
        aoe2mc.main([str(c), str(tmp_path / "out")])
    msg = str(e.value.code)
    assert "(.scn, .scx)" in msg and "  2 Alt.scx\n  3 Karte.scn" in msg and "Gut" not in msg
    assert "2 Alt.scx: " in out.getvalue() and "does not decompress" in out.getvalue()   # 3 Karte.scn: not tried (#3863)
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["1 Gut", "2 Alt.scx", "3 Karte.scn", "campaign.json"]
    assert (tmp_path / "out" / "1 Gut" / "level.dat").exists()
