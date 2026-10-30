"""The Paper plugin of the game program (#435): aoe moveto walks on a Minecraft path, aoe attack sets a target."""
import os
import re
import shutil
import time

import pytest

from game import run


def test_plugin_jar_name_follows_the_source(tmp_path, monkeypatch):
    """The jar name has the hash of the source: a changed source gives a new build, the same source none."""
    monkeypatch.setattr(run.mc_check, "CACHE", str(tmp_path / "mc"))
    built = []

    def build(version, path):
        built.append(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").close()
    monkeypatch.setattr(run, "build_plugin", build)
    a = run.plugin_jar("26.3")
    assert run.plugin_jar("26.3") == a and len(built) == 1
    assert os.path.basename(a).startswith("aoe2mc-") and os.path.dirname(a) == str(tmp_path / "plugin")


def pos(game, tag):
    m = re.search(r"\[(-?[\d.]+)d, (-?[\d.]+)d, (-?[\d.]+)d\]", game.command(f"data get entity @e[tag={tag},limit=1] Pos"))
    return tuple(map(float, m.groups())) if m else None


@pytest.mark.mc
def test_unit_walks_around_a_wall(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a pen in the air, inside the world border (no path outside it)
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 16} {z0 + 16}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 13} {y + 3} {z0 + 13} stone_bricks hollow")  # floor, roof
        game.command(f"fill {x0} {y} {z0 + 6} {x0 + 9} {y + 2} {z0 + 6} stone_bricks")   # the gap is at x0+10..12
        game.command(f"summon cow {x0 + 2.5} {y} {z0 + 2.5} {{NoAI:1b,Tags:[\"u\"]}}")
        game.command(f"summon cow {x0 + 11.5} {y} {z0 + 2.5} {{NoAI:1b,Tags:[\"v\"]}}")
        goal = (x0 + 2.5, y, z0 + 10.5)
        assert game.command(f"aoe moveto @e[tag=u] {goal[0]} {goal[1]} {goal[2]}").strip() == "Moved 1 units"
        end, xmax, p = time.time() + 30, 0, None
        while time.time() < end:
            p = pos(game, "u")
            xmax = max(xmax, p[0])
            if abs(p[0] - goal[0]) < 1.5 and abs(p[2] - goal[2]) < 1.5:
                break
            time.sleep(0.2)
        assert abs(p[0] - goal[0]) < 1.5 and abs(p[2] - goal[2]) < 1.5, p
        assert xmax > x0 + 10, xmax                           # around the wall, not through it
        assert game.command("aoe attack @e[tag=v] @e[tag=u,limit=1]").strip() == "Attack: 1 units"
        assert game.command("aoe moveto @e[tag=none] 0 0 0").strip() == "Moved 0 units"
