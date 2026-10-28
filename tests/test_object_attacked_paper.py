"""The trigger condition "Object Attacked" fires on an AoE2 hit of the game program (#3085): the plugin cancels the
vanilla hit, so HurtTime stays 0, and sets the tag aoe2mc.hit for 10 ticks; the predicate aoe2mc:attacked tests both."""
import json
import os
import shutil
import time

import pytest

import aoe2mc
from game import combat, run
from test_damage import health


@pytest.mark.mc
def test_an_aoe2_hit_fires_object_attacked(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    pred = world / "datapacks" / "aoe2mc" / "data" / "aoe2mc" / "predicate" / "attacked.json"
    os.makedirs(pred.parent, exist_ok=True)
    meta = world / "datapacks" / "aoe2mc" / "pack.mcmeta"         # the tiny world can have no datapack
    if not meta.exists():
        f = aoe2mc.MC["pack_format"]
        meta.write_text(json.dumps({"pack": {"description": "t", "pack_format": f, "min_format": f, "max_format": f}}))
    pred.write_text(json.dumps(aoe2mc.attacked_predicate()))
    x0, y, z0 = 1, 200, 1
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 20} {z0 + 20}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 16} {y - 1} {z0 + 16} stone_bricks")
        game.command("reload")
        game.command("time set midnight")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        # a: a militia with the reference 5; b attacks it. k: a knight (the horse) with its rider r (reference 6); c attacks k
        game.command(f'summon zombie {x0 + 2.5} {y} {z0 + 2.5} {{NoAI:1b,Tags:["a","aoe2mc.r5"]}}')
        game.command(f'summon zombie {x0 + 4.5} {y} {z0 + 2.5} {{NoAI:1b,Tags:["b"]}}')
        game.command(f'summon horse {x0 + 2.5} {y} {z0 + 10.5} {{NoAI:1b,Tame:1b,Tags:["k"],'
                     f'Passengers:[{{id:"zombie",NoAI:1b,Tags:["r","aoe2mc.r6"]}}]}}')
        game.command(f'summon zombie {x0 + 4.5} {y} {z0 + 10.5} {{NoAI:1b,Tags:["c"]}}')
        for tag, team, name in (("a", "p1", "MILITIA"), ("b", "p2", "MILITIA"), ("k", "p1", "KNIGHT"),
                                ("c", "p2", "MILITIA")):
            game.command(f"team join {team} @e[tag={tag}]")
            assert game.command(combat.stats_command(f"@e[tag={tag},limit=1]", name)).strip() == "Stats: 1 units"
        game.command("team join p1 @e[tag=r]")
        start = {t: health(game, t) for t in ("a", "k")}
        assert game.command("aoe attack @e[tag=b] @e[tag=a,limit=1]").strip() == "Attack: 1 units"
        assert game.command("aoe attack @e[tag=c] @e[tag=k,limit=1]").strip() == "Attack: 1 units"
        seen, end = set(), time.time() + 30
        while time.time() < end and len(seen) < 2:
            for ref in (5, 6):
                if "passed" in game.command(f"execute if entity @e[tag=aoe2mc.r{ref},predicate=aoe2mc:attacked]"):
                    seen.add(ref)
            time.sleep(0.1)
        assert health(game, "a") < start["a"] and health(game, "k") < start["k"]
        assert seen == {5, 6}
