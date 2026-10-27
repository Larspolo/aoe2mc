"""Check 3 of #1138 (after #1657): the conquest end with a bot. The setup of game/run.py --play --cheats --bot on Paper,
a real client. The bot (player 2) builds; then the player types "torpedo2" in the chat. Expected: "Player 2 is
defeated.", the "Victory" title, no entity of player 2 and no block of the bot's sites one minute later. Usage: OUTDIR"""
import contextlib, io, json, os, shutil, sys, time
ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import aoe2mc, scenarios, run, gather, combat, mc_shot, bot as bots  # noqa
from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.units import UnitInfo

out = sys.argv[1]
P1, P2 = scenarios.PlayerId.ONE, scenarios.PlayerId.TWO
scn = scenarios.new_scenario(48)
um = scn.unit_manager
um.add_unit(P1, BuildingInfo.TOWN_CENTER.ID, x=12, y=12)
um.add_unit(P1, UnitInfo.VILLAGER_MALE.ID, x=16.5, y=8.5)
um.add_unit(P2, BuildingInfo.TOWN_CENTER.ID, x=34, y=34)
for i in range(4):
    um.add_unit(P2, UnitInfo.VILLAGER_MALE.ID, x=30.5 + i, y=29.5)
src, world = os.path.join(out, "bot.aoe2scenario"), os.path.join(out, "W3")
scenarios.save(scn, src)
shutil.rmtree(world, ignore_errors=True)
with contextlib.redirect_stdout(io.StringIO()):
    aoe2mc.convert(src, world)
data = json.load(open(os.path.join(world, "aoe2mc.json")))
tc2 = next((o["footprint"][0] + 1, o["footprint"][1] + 1) for o in data["objects"]
           if o["kind"] == "building" and o["name"] == "TOWN_CENTER" and o["player"] == 2)
ME = "aoe2mc"
res = {}


def say(c, text):
    c.key("t")
    time.sleep(1)
    c.xdo("type", "--delay", 50, text)
    c.key("Return")
    time.sleep(1)


with run.Game(world) as game:
    game.forceload()
    end = time.time() + 60
    while True:
        g = gather.Gather(game, data, cheats=True).setup()
        if g.villagers:
            break
        assert time.time() < end
        time.sleep(1)
    b = bots.Bot(game, data, share=g, attack=9999).setup()
    g.bots = [b]
    combat.setup(game, data)
    for r in ("food", "wood", "gold", "stone"):
        b.g.stock[r] += 2000                                           # the bot builds at once
    with mc_shot.Client(game.game_port, game.version) as c:
        c.wait_join(lambda: ME in game.command("list"))
        game.command(f"gamemode adventure {ME}")
        x, z = tc2
        t0 = time.time()
        g.run(240, until=lambda: sum(bool(s.get("done")) for s in b.g.sites) >= 2)
        sites = [dict(name=s["name"], footprint=s["footprint"], done=bool(s.get("done"))) for s in b.g.sites]
        res["before"] = {"s": round(time.time() - t0), "sites": sites, "queues": {str(k): v for k, v in b.g.queues.items()},
                         "p2": game.command("execute if entity @e[tag=aoe2mc.p2]")}
        print("before", json.dumps(res["before"], default=str), flush=True)
        game.command(f"tp {ME} {x} {g.map.y(x, z) + 22} {z + 30} 180 35")
        time.sleep(6)
        c.shot(os.path.join(out, "3-bot-before.png"))
        say(c, "torpedo2")
        t0 = time.time()
        g.run(30, until=lambda: g.ended)
        for i, w in enumerate((0, 0.5, 1.0)):
            time.sleep(w)
            c.shot(os.path.join(out, f"3-bot-victory-{i}.png"))
        res["end"] = {"ended": g.ended, "s": round(time.time() - t0, 1), "bots": len(g.bots),
                      "chat": [ln for ln in c.text().splitlines() if "[CHAT]" in ln][-5:]}
        print("end", json.dumps(res["end"]), flush=True)
        time.sleep(60)                                                 # the bot queue spawned units here before #1657
        res["after"] = {"p2": game.command("execute if entity @e[tag=aoe2mc.p2]"),
                        "p2_team": game.command("execute if entity @e[team=p2,type=!player]")}
        c.shot(os.path.join(out, "3-bot-after.png"))
        left = {}
        for s in sites:                                                # fill counts only the blocks that it changes
            x0, x1, z0, z1 = s["footprint"]
            bx0, y0, bz0, bx1, y1, bz1 = combat.building_box({"footprint": [x0, z0, x1, z1]}, g.map.ground)
            left[s["name"] + str(s["footprint"])] = game.command(f"fill {bx0} {y0 + 1} {bz0} {bx1} {y1} {bz1} minecraft:air")
        res["after"]["site_blocks"] = left
        print("after", json.dumps(res["after"]), flush=True)
json.dump(res, open(os.path.join(out, "3-result.json"), "w"), indent=1, default=str)
print("done", flush=True)
