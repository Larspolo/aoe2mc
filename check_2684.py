"""Check of #2684: a walk speed bonus (Celts: infantry +5 % in the Dark Age, civs.UNITS) and a start resource bonus
(Persians: food +50, wood +50, civs.START) of the game program on Paper, with a real client. The same world runs
three times with player 1 as CELTS, BRITONS and PERSIANS (the --civ setting of run.play: aoe2mc.json "players").
The militia walks with the move order of the player (Gather.select, Gather.walk_to). Usage: OUTDIR"""
import contextlib, io, json, os, re, shutil, sys, time
ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import aoe2mc, scenarios, run, gather, ai, train, civs, mc_shot  # noqa
from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.units import UnitInfo

out = sys.argv[1]
P1 = scenarios.PlayerId.ONE
scn = scenarios.new_scenario(40)
um = scn.unit_manager
um.add_unit(P1, BuildingInfo.TOWN_CENTER.ID, x=8, y=8)
um.add_unit(P1, UnitInfo.MILITIA.ID, x=10.5, y=20.5)
um.add_unit(P1, UnitInfo.VILLAGER_MALE.ID, x=12.5, y=12.5)
src, world = os.path.join(out, "check.aoe2scenario"), os.path.join(out, "W")
scenarios.save(scn, src)
shutil.rmtree(world, ignore_errors=True)
with contextlib.redirect_stdout(io.StringIO()):
    aoe2mc.convert(src, world)
base = json.load(open(os.path.join(world, "aoe2mc.json")))
MIL = next(o["uuid"] for o in base["objects"] if o["kind"] == "unit" and o["name"] == "MILITIA")
ME = "aoe2mc"


def pos(game, u):
    return tuple(map(float, re.findall(r"(-?[\d.]+)d", game.command(f"data get entity {u} Pos"))[:3]))


res = {}
for civ in ("CELTS", "BRITONS", "PERSIANS"):
    data = json.loads(json.dumps(base))
    data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    r = res[civ] = {}
    with run.Game(world) as game:
        game.forceload()
        end = time.time() + 60
        while True:
            g = gather.Gather(game, data, resources="standard").setup()
            if g.villagers and MIL in g.soldiers:
                break
            assert time.time() < end
            time.sleep(1)
        r["civ"], r["stock"] = civs.civ(g), {k: g.stock[k] for k in ("food", "wood", "gold", "stone")}
        r["board"] = {k: game.command(f"scoreboard players get {k.capitalize()} {g.board}")
                      for k in ("food", "wood", "gold", "stone")}
        with mc_shot.Client(game.game_port, game.version) as c:
            c.wait_join(lambda: ME in game.command("list"))
            game.command(f"gamemode adventure {ME}")
            x, y, z = pos(game, MIL)
            game.command(f"tp {ME} {x + 8} {y + 3} {z + 12} 150 15")
            g.select(MIL)
            r["train_speed"] = train.speed(g, "MILITIA", MIL)
            r["expected_attr"] = ai.movement_speed("MILITIA", g.map.T, gather.NORMAL * r["train_speed"])
            cell = (int(x) + 60, int(z))
            g.walk_to("MILITIA", cell)
            time.sleep(1.5)
            a, t0 = pos(game, MIL), time.monotonic()
            time.sleep(4)
            b, t1 = pos(game, MIL), time.monotonic()
            r["attr"] = game.command(f"attribute {MIL} minecraft:movement_speed get")
            r["blocks_per_s"] = round(((b[0] - a[0]) ** 2 + (b[2] - a[2]) ** 2) ** 0.5 / (t1 - t0), 3)
            r["bar"] = game.command("bossbar get aoe2mc:sel_p1 max")
            time.sleep(2)
            c.shot(os.path.join(out, f"{civ.lower()}.png"))
        print(civ, json.dumps(r), flush=True)
json.dump(res, open(os.path.join(out, "result.json"), "w"), indent=1)
