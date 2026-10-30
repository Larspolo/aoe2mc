"""#4564: a saved game of DE (.aoe2spgame, .aoe2mpgame) converts as the state of its header (read_saved). The test
cuts the header block of a record: a save has the same form (docs/research/saved-games.md)."""
import os

import pytest

import aoe2mc

SAMPLES = os.path.join(os.path.dirname(__file__), os.pardir, "samples")
RECORD = os.path.join(SAMPLES, "de-64.3.aoe2record")


def cut(tmp_path, name="cut.aoe2spgame"):
    data = open(RECORD, "rb").read()
    path = tmp_path / name
    path.write_bytes(data[:int.from_bytes(data[:4], "little")])
    return str(path)


def test_a_header_only_save_gives_the_players_owners_and_positions_of_the_record(tmp_path):
    saved = aoe2mc.read_map(cut(tmp_path))
    record = aoe2mc.read_record(RECORD)
    assert saved[0] == record[0] and (saved[1] == record[1]).all()
    assert set(saved[6]) == set(record[6]) and len(saved[6]) > 2
    where = lambda objs: sorted((o["player"], o["name"], o["x"], o["y"]) for o in objs)
    assert where(saved[5]) == where(record[5])
    assert {o["player"] for o in saved[5]} >= {1, 2}


def test_a_multiplayer_save_reads_too(tmp_path):
    assert aoe2mc.read_map(cut(tmp_path, "cut.aoe2mpgame"))[0] > 0


@pytest.mark.parametrize("data", [b"", b"not a saved game at all", bytes(64)])
def test_a_file_that_is_not_a_save_gives_one_line(tmp_path, data):
    path = tmp_path / "bad.aoe2spgame"
    path.write_bytes(data)
    with pytest.raises(SystemExit) as e:
        aoe2mc.read_map(str(path))
    assert "not a saved game" in str(e.value) and "\n" not in str(e.value)


def test_the_sample_save_converts_when_it_is_there():
    path = os.path.join(SAMPLES, "aoe2mc-sample.aoe2spgame")
    if not os.path.exists(path):
        pytest.skip("no sample save")
    assert aoe2mc.read_saved(path)[5]
