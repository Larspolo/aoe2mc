"""Check #1655: diagonal gates built in the game program on a Paper server, then in-game screenshots."""
import contextlib, io, json, math, shutil, subprocess, sys, time
sys.path[:0] = ["/home/user/aoe2mc", "/home/user/aoe2mc/game", "/home/user/aoe2mc/tools"]
import aoe2mc, scenarios, mc_shot
from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from game import build, gather, run

D = sys.argv[1]
scn = scenarios.new_scenario(16)
scn.unit_manager.add_unit(scenarios.PlayerId.ONE, BuildingInfo.TOWN_CENTER.ID, x=4, y=4)
scenarios.save(scn, f"{D}/g.aoe2scenario")
shutil.rmtree(f"{D}/W", ignore_errors=True)
with contextlib.redirect_stdout(io.StringIO()):
    aoe2mc.convert(f"{D}/g.aoe2scenario", f"{D}/W")
data = json.load(open(f"{D}/W/aoe2mc.json"))
T = 4
c = lambda tx, tz: (tx * T + 2, tz * T + 2)
with run.Game(f"{D}/W") as game, mc_shot.Client(game.game_port, game.version) as client:
    client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
    game.command("gamemode spectator aoe2mc")
    game.command("time set noon")
    game.forceload()
    g = gather.Gather(game, data, tick=0.25, start={}).setup()
    g.techs = {"FEUDAL_AGE"}
    g.stock.update(wood=5000, stone=5000)
    for name, gate, a, b, mid in (("PALISADE_WALL", "PALISADE_GATE", (8, 1), (14, 7), (11, 4)),
                                  ("STONE_WALL", "GATE", (1, 14), (7, 8), (4, 11))):
        build.wall(g, "nobody", name, c(*a))
        build.wall(g, "nobody", name, c(*b))
        for s in list(g.sites):
            build.rise(g, s, math.inf)
        site = build.gate(g, "nobody", gate, c(*mid))
        print(gate, site and (site["footprint"], site.get("way")))
        build.rise(g, site, math.inf)
    time.sleep(3)
    for i, (x, y, z, yaw, pitch) in enumerate([(58, 72, 6, 45, 28), (34, 72, 30, -135, 28), (6, 72, 34, -45, 28), (30, 72, 58, 135, 28)]):
        game.command(f"tp aoe2mc {x} {y} {z} {yaw} {pitch}")
        time.sleep(8)
        client.shot(f"{D}/view{i + 1}.png")
print("done")
