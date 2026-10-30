"""mc_shot.py loads a world that the Paper server played (#4617)."""
import os
import sys

from nbtlib import List, String, load

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import aoe2mc  # noqa: E402
import mc_shot  # noqa: E402


def test_paper_world_gets_vanilla(tmp_path):
    aoe2mc.write_level_dat(str(tmp_path / "level.dat"), "W", (1, 2, 3))
    f = load(str(tmp_path / "level.dat"))
    f["Data"]["DataPacks"]["Enabled"] = List[String]([String("vanilla"), String("file/aoe2mc"), String("paper")])
    f.save()
    gen = tmp_path / "data" / "minecraft" / "world_gen_settings.dat"
    os.remove(gen)
    mc_shot.vanilla_world(str(tmp_path))
    data = load(str(tmp_path / "level.dat"))["Data"]
    assert [str(p) for p in data["DataPacks"]["Enabled"]] == ["vanilla", "file/aoe2mc"]
    assert "dimensions" in load(str(gen))["data"]


def test_vanilla_world_keeps_files(tmp_path):
    aoe2mc.write_level_dat(str(tmp_path / "level.dat"), "W", (1, 2, 3), rain=True)
    mc_shot.vanilla_world(str(tmp_path))
    assert int(load(str(tmp_path / "data" / "minecraft" / "weather.dat"))["data"]["raining"]) == 1
