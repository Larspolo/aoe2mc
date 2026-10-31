"""tools/mc_shot.py: the data pack and the library rules, and a real client run on the tiny world (marker mc)."""
import json
import shutil

import mc_shot
import numpy as np
import pytest
from test_mc_check import mojang_reachable


def test_library_rules_for_linux():
    assert mc_shot.allowed({})
    assert mc_shot.allowed({"rules": [{"action": "allow", "os": {"name": "linux"}}]})
    assert not mc_shot.allowed({"rules": [{"action": "allow", "os": {"name": "osx"}}]})
    assert not mc_shot.allowed({"rules": [{"action": "allow"}, {"action": "disallow", "os": {"name": "linux"}}]})


def test_data_pack_shows_each_view(tmp_path):
    mc_shot.add_data_pack(str(tmp_path), [(1, 70, 2, 90, 20), (5, 80, 6, -45, 30)], 48, 200)
    root = tmp_path / "datapacks" / "aoe2mc_shot"
    assert json.loads((root / "pack.mcmeta").read_text())["pack"]["pack_format"] == 48
    tick = (root / "data" / "aoe2mc_shot" / "function" / "tick.mcfunction").read_text()
    assert "gamemode spectator @a[scores={aoe2mc_t=1}]" in tick
    assert "execute as @a[scores={aoe2mc_t=40}] run tp @s 1 70 2 90 20" in tick
    assert 'tellraw @a[scores={aoe2mc_t=240}] "aoe2mc view 2"' in tick


@pytest.mark.mc
def test_screenshot_of_tiny_world(tiny_world, tmp_path):
    if not shutil.which("Xvfb") or not mojang_reachable():
        pytest.skip("Xvfb or Mojang is not available")
    from PIL import Image
    out = mc_shot.shoot(tiny_world[0], str(tmp_path / "shot.png"), [(40, 70, 75, 180, 25)])
    img = np.asarray(Image.open(out[0]).convert("RGB"), np.float32)
    assert img.shape == (720, 1280, 3)
    assert img.std() > 20             # a world, not one color (a menu or a black screen)
