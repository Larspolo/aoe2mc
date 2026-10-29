"""Ranged units shoot from their AoE2 range (#515): game/combat.py range_command and the plugin goal on Paper."""
import math
import re
import shutil
import time

import pytest

from game import ai, combat, run


def test_range_command():
    # archer: range tiles * 4 blocks, reload game seconds / Normal speed (1.7) in ticks
    s = combat.stats("ARCHER")
    assert combat.range_command("u-1", "ARCHER", 4) == f"aoe range u-1 {s.range * 4} {round(s.reload / combat.NORMAL * 20)}"
    assert combat.range_command("u-1", "ARCHER", 2, rate=1.0) == f"aoe range u-1 {s.range * 2} {round(s.reload * 20)}"
    assert combat.range_command("u-2", "MILITIA", 4) is None and combat.range_command("u-3", "MONK", 4) is None

    class Game:
        sent = []

        def command(self, c):
            self.sent.append(c)
            return "Stats: 1 units"
    data = {"tile_size": 3, "objects": [{"kind": "unit", "player": 1, "name": "ARCHER", "uuid": "a"},
                                        {"kind": "unit", "player": 2, "name": "MILITIA", "uuid": "m"}]}
    assert combat.setup(Game(), data) == 2
    assert Game.sent == [combat.range_command("a", "ARCHER", 3), combat.stats_command("a", "ARCHER"),
                         combat.stats_command("m", "MILITIA"),
                         combat.sight_command("a", "ARCHER", 3), combat.sight_command("m", "MILITIA", 3),   # (#775)
                         ai.speed_command("a", "ARCHER", 3), ai.speed_command("m", "MILITIA", 3)]


def data(game, tag, path):
    out = game.command(f"data get entity @e[tag={tag},limit=1] {path}")
    m = re.findall(r"-?[\d.]+(?=[dfs]?\b)", out.split(":", 1)[-1])
    return [float(v) for v in m] if "has the following" in out else None


@pytest.mark.mc
def test_archer_shoots_from_its_aoe2_range(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 44} {z0 + 8}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 42} {y - 1} {z0 + 6} stone_bricks")
        game.command("time set midnight")
        game.command("difficulty hard")       # a skeleton aims better on hard: fewer misses
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        game.command(f'summon skeleton {x0 + 0.5} {y} {z0 + 2.5} {{NoAI:1b,Tags:["a"],'
                     'equipment:{mainhand:{id:"minecraft:bow",count:1}}}')
        game.command(f'summon zombie {x0 + 36.5} {y} {z0 + 2.5} {{NoAI:1b,IsBaby:0b,Tags:["t"]}}')
        game.command("team join p1 @e[tag=a]")
        game.command("team join p2 @e[tag=t]")
        assert game.command(combat.range_command("@e[tag=a,limit=1]", "ARCHER", 4)).strip() == "Range: 1 units"
        game.command(combat.stats_command("@e[tag=a,limit=1]", "ARCHER"))
        game.command("aoe stats @e[tag=t,limit=1] 1000 0 0 0 0 infantry -")    # many hit points, 4 per arrow
        assert game.command("aoe attack @e[tag=a] @e[tag=t,limit=1]").strip() == "Attack: 1 units"
        assert "aoe_range" in game.command("aoe goals @e[tag=a,limit=1]")
        hits, last, end = [], 1000.0, time.time() + 40
        while time.time() < end and len(hits) < 8:
            h = (data(game, "t", "Health") or [last])[0]
            if h < last:
                hits.append(time.time())
                last = h
            time.sleep(0.05)
        a, t = data(game, "a", "Pos"), data(game, "t", "Pos")
        d = math.hypot(a[0] - t[0], a[2] - t[2])
        s = combat.stats("ARCHER")
        reach, ticks = s.range * 4, round(s.reload / combat.NORMAL * 20)
        assert reach - 3 <= d <= reach + 0.5, d     # it stopped at its range (tiles * 4 blocks), not next to the target
        assert len(hits) >= 5, hits
        gaps = sorted(b - a for a, b in zip(hits, hits[1:]))
        assert gaps[0] == pytest.approx(ticks / 20, abs=0.25), gaps       # one shot per reload, a miss skips a hit
        assert gaps[len(gaps) // 2] < 2 * ticks / 20, gaps
