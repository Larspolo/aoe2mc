"""Images of #1656: a closed and an open portcullis (stone GATE, build.portcullis, Gates.java) with a real client."""
import os, shutil, sys, time, types
ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, os.path.join(ROOT, "game"), os.path.join(ROOT, "tools"), os.path.join(ROOT, "tests")]
import contextlib, io
import aoe2mc, scenarios, run, build, mc_shot  # noqa
out = sys.argv[1]
src, world = os.path.join(out, "t.aoe2scenario"), os.path.join(out, "W")
scenarios.tiny(src)
shutil.rmtree(world, ignore_errors=True)
with contextlib.redirect_stdout(io.StringIO()):
    aoe2mc.convert(src, world)
x0, y, z0, n = 1, 200, 1, 30
gx, wz = x0 + 8, z0 + 12
with run.Game(world) as game:
    game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + n + 2} {z0 + n + 2}")
    game.command(f"fill {x0} {y - 1} {z0} {x0 + n} {y - 1} {z0 + n} grass_block")
    game.command(f"fill {x0} {y} {wz - 1} {x0 + n} {y + 5} {wz + 1} stone_bricks")
    game.command(f"fill {gx + 1} {y} {wz - 1} {gx + 2} {y + 3} {wz + 1} air")
    game.command("time set noon")
    game.command("team add p1")
    g = types.SimpleNamespace(command=game.command, paper=True, map=types.SimpleNamespace(T=1, y=lambda x, z: y))
    build.portcullis(g, {"name": "GATE", "player": 1, "footprint": (gx, gx + 4, wz - 1, wz + 2)})
    with mc_shot.Client(game.game_port, game.version) as c:
        c.wait_join(lambda: "aoe2mc" in game.command("list"))
        game.command("gamemode spectator aoe2mc")
        game.command(f"tp aoe2mc {gx + 2} {y + 2.5} {wz - 7} 0 10")
        time.sleep(6)
        c.shot(os.path.join(out, "closed.png"))
        game.command(f'summon zombie {gx + 2} {y} {wz - 2.5} {{NoAI:1b,IsBaby:0b,Tags:["own"]}}')
        game.command("team join p1 @e[tag=own]")
        time.sleep(2)
        print("open:", game.command(f"execute if block {gx + 1} {y} {wz} minecraft:air"))
        c.shot(os.path.join(out, "open.png"))
