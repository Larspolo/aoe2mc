"""Units with their Minecraft AI, but only the AoE2 goals (#436): game/ai.py and the plugin on Paper."""
import re
import shutil
import time

import pytest

from game import ai, run


def test_movement_speed_follows_the_aoe2_speed():
    # tiles per game second * tile size 4 * Normal speed = blocks per second
    tiles = next(s for k, s in ai.SPEEDS.items() if "VILLAGER".startswith(k))
    assert ai.walk_speed("VILLAGER", 4) == pytest.approx(tiles * 4 * ai.NORMAL)
    assert ai.WALK * ai.movement_speed("VILLAGER", 4) ** 2 == pytest.approx(ai.walk_speed("VILLAGER", 4), rel=1e-3)
    assert ai.movement_speed("VILLAGER", 2) < ai.movement_speed("VILLAGER", 4)       # smaller tiles: slower
    assert ai.walk_speed("SOMETHING_ELSE", 4) == pytest.approx(4 * ai.NORMAL)          # 1 tile per second


def test_orders_set_the_speed_first():
    class Game:
        def __init__(self):
            self.sent = []

        def command(self, c):
            self.sent.append(c)
            return "ok"
    g = Game()
    ai.move(g, "u-1", "KNIGHT", 4, 10.5, 64, 3.5)
    ai.attack(g, ["u-2", "u-3"], ["MILITIA", "ARCHER"], 4, "u-9")
    assert g.sent == [ai.speed_command("u-1", "KNIGHT", 4), "aoe moveto u-1 10.5 64 3.5",
                      ai.speed_command("u-2", "MILITIA", 4), ai.speed_command("u-3", "ARCHER", 4),
                      "aoe attack u-2 u-9", "aoe attack u-3 u-9"]
    assert g.sent[0] == f"attribute u-1 minecraft:movement_speed base set {ai.movement_speed('KNIGHT', 4)}"


def data(game, tag, path):
    out = game.command(f"data get entity @e[tag={tag},limit=1] {path}")
    m = re.findall(r"-?[\d.]+(?=[dfs]?\b)", out.split(":", 1)[-1])
    return [float(v) for v in m] if "has the following" in out else None


@pytest.mark.mc
def test_units_keep_only_aoe2_goals(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 40} {z0 + 16}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 36} {y - 1} {z0 + 12} stone_bricks")
        game.command("time set midnight")                              # no fire before the orders
        game.command("difficulty easy")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        units = {"a": (2, "p1"), "b": (4, "p1"), "c": (8, "p2")}
        for tag, (dx, team) in units.items():
            game.command(f'summon zombie {x0 + dx + 0.5} {y} {z0 + 2.5} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join {team} @e[tag={tag}]")
        game.command(f'summon villager {x0 + 5.5} {y} {z0 + 4.5} {{NoAI:1b,Tags:["v"]}}')   # zombies hunt villagers
        game.command("team join p1 @e[tag=v]")
        start = {}
        for tag in units:                     # an order to stay turns the AI on
            p = data(game, tag, "Pos")
            start[tag] = p
            assert game.command(f"aoe moveto @e[tag={tag}] {p[0]} {p[1]} {p[2]}").strip() == "Moved 1 units"
        game.command("time set noon")                                  # zombies burn in the sun in vanilla
        time.sleep(30)
        for tag in units:
            p = data(game, tag, "Pos")
            assert p and abs(p[0] - start[tag][0]) < 1.5 and abs(p[2] - start[tag][2]) < 1.5, (tag, p)   # no stroll
            assert data(game, tag, "Health") == [20.0], tag                                 # no fire, no fight
            assert data(game, tag, "NoAI") is None or data(game, tag, "NoAI") == [0.0]
        assert data(game, "v", "Health") == [20.0]                                         # nobody attacked
        assert game.command("aoe attack @e[tag=b] @e[tag=a,limit=1]").strip() == "Attack: 0 units"   # same team
        assert game.command("aoe attack @e[tag=c] @e[tag=a,limit=1]").strip() == "Attack: 1 units"
        end = time.time() + 15
        while time.time() < end and (data(game, "a", "Health") or [20.0])[0] >= 20:
            time.sleep(0.5)
        assert (data(game, "a", "Health") or [0.0])[0] < 20                                 # the attack goal stays
        # the walk speed of a militia at tile size 4 (6.12 blocks per second) on a straight way of 24 blocks
        game.command(f'summon zombie {x0 + 0.5} {y} {z0 + 10.5} {{NoAI:1b,IsBaby:0b,Tags:["m"]}}')
        ai.move(game, "@e[tag=m,limit=1]", "MILITIA", 4, x0 + 30.5, y, z0 + 10.5)
        t, a = time.time() + 15, None
        while time.time() < t:
            p = data(game, "m", "Pos")
            if a is None and p[0] > x0 + 4:
                a = (time.time(), p[0])
            if p[0] > x0 + 28:
                break
            time.sleep(0.05)
        speed = (p[0] - a[1]) / (time.time() - a[0])
        assert speed == pytest.approx(ai.walk_speed("MILITIA", 4), rel=0.25), speed
