"""A conversion into a folder with an earlier aoe2mc world gives the same world as a new folder: the old outputs go,
the files of other worlds stay (#3030, _convert)."""
import os

import pytest

import aoe2mc
import scenarios
import world_diff

OVERWORLD = os.path.join("dimensions", "minecraft", "overworld")


def region(path, name):
    """A dummy region file of an earlier conversion (bytes, not a real .mca: the test only checks the file)."""
    os.makedirs(os.path.join(path, OVERWORLD, "region"), exist_ok=True)
    with open(os.path.join(path, OVERWORLD, "region", name), "wb") as f:
        f.write(b"old")


def test_a_folder_of_an_earlier_world_gives_the_same_world(tmp_path):
    a = scenarios.triggers(str(tmp_path / "A.aoe2scenario"))
    b = scenarios.tiny(str(tmp_path / "B.aoe2scenario"))
    aoe2mc.convert(a, str(tmp_path / "W"))
    aoe2mc.convert(b, str(tmp_path / "W"))                    # the second world into the same folder
    aoe2mc.convert(b, str(tmp_path / "W2"))
    assert world_diff.diff(str(tmp_path / "W"), str(tmp_path / "W2")) == []


def test_the_pack_of_an_earlier_world_goes_with_ambience_off(tmp_path):
    a = scenarios.triggers(str(tmp_path / "A.aoe2scenario"))
    aoe2mc.convert(a, str(tmp_path / "W"))
    assert os.path.exists(tmp_path / "W" / "datapacks" / "aoe2mc")
    aoe2mc.convert(a, str(tmp_path / "W"), ambience="off")
    assert not os.path.exists(tmp_path / "W" / "datapacks" / "aoe2mc")


def test_old_region_files_go_and_the_players_folder_stays(tmp_path):
    b = scenarios.tiny(str(tmp_path / "B.aoe2scenario"))
    aoe2mc.convert(b, str(tmp_path / "W"))
    region(tmp_path / "W", "r.5.5.mca")
    os.makedirs(tmp_path / "W" / "players", exist_ok=True)
    (tmp_path / "W" / "players" / "me.dat").write_bytes(b"mine")
    aoe2mc.convert(b, str(tmp_path / "W"))
    assert not os.path.exists(tmp_path / "W" / OVERWORLD / "region" / "r.5.5.mca")
    assert (tmp_path / "W" / "players" / "me.dat").read_bytes() == b"mine"


def test_a_folder_of_another_world_keeps_its_files(tmp_path):
    b = scenarios.tiny(str(tmp_path / "B.aoe2scenario"))
    region(tmp_path / "F", "r.5.5.mca")                      # no aoe2mc.json: a world of another program
    aoe2mc.convert(b, str(tmp_path / "F"))
    assert (tmp_path / "F" / OVERWORLD / "region" / "r.5.5.mca").read_bytes() == b"old"


def test_an_option_error_keeps_the_old_world(tmp_path):
    b = scenarios.tiny(str(tmp_path / "B.aoe2scenario"))
    aoe2mc.convert(b, str(tmp_path / "W"))
    with pytest.raises(aoe2mc.OptionError):
        aoe2mc.convert(b, str(tmp_path / "W"), player_arch=[(9, "western")])
    assert os.path.exists(tmp_path / "W" / "aoe2mc.json")
    assert os.path.exists(tmp_path / "W" / "datapacks" / "aoe2mc")
