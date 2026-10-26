"""Check of #964: the bot of player 2 on Paper (game/run.py --play --bot setup), with a real client. Usage: OUTDIR"""
import contextlib, io, json, os, shutil, sys, time
ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import aoe2mc, scenarios, run, gather, combat, bot, train, mc_shot  # noqa
from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.other import OtherInfo
from AoE2ScenarioParser.datasets.units import UnitInfo

out = sys.argv[1]
P1, P2, GAIA = scenarios.PlayerId.ONE, scenarios.PlayerId.TWO, scenarios.PlayerId.GAIA
scn = scenarios.new_scenario(40)
um = scn.unit_manager
um.add_unit(P1, BuildingInfo.TOWN_CENTER.ID, x=8, y=8)
for i in range(3):
    um.add_unit(P1, UnitInfo.VILLAGER_MALE.ID, x=12.5, y=6.5 + i)
um.add_unit(P2, BuildingInfo.TOWN_CENTER.ID, x=30, y=30)
for i in range(6):
    um.add_unit(P2, UnitInfo.VILLAGER_FEMALE.ID, x=33.5, y=27.5 + i)
res = [("TREE_OAK_FOREST", 36.5 + dx, 22.5 + dy) for dx in range(3) for dy in range(4)] + \
      [("FRUIT_BUSH", 24.5 + i, 35.5) for i in range(4)] + [("GOLD_MINE", 24.5 + i, 24.5) for i in range(2)] + \
      [("STONE_MINE", 35.5, 36.5 + i) for i in range(2)]
for name, x, y in res:
    um.add_unit(GAIA, getattr(OtherInfo, name).ID, x=x, y=y)
src, world = os.path.join(out, "bot.aoe2scenario"), os.path.join(out, "W")
scenarios.save(scn, src)
shutil.rmtree(world, ignore_errors=True)
with contextlib.redirect_stdout(io.StringIO()):
    aoe2mc.convert(src, world)
data = json.load(open(os.path.join(world, "aoe2mc.json")))
ATTACK, END = 480.0, 900.0                       # AoE2 seconds: attack at 8:00, end at 15:00
with run.Game(world) as game:
    game.forceload()
    end = time.time() + 60
    while True:
        me = gather.Gather(game, data).setup()
        b = bot.Bot(game, data, share=me, attack=ATTACK).setup()
        if me.villagers and len(b.g.villagers) == 6:
            break
        assert time.time() < end, "the villagers did not load"
        time.sleep(1)
    me.bots = [b]
    combat.setup(game, data)
    with mc_shot.Client(game.game_port, game.version) as c:
        c.wait_join(lambda: "aoe2mc" in game.command("list"))
        game.command("gamemode spectator aoe2mc")
        rows, first = [], None
        for at in (120, 300, 480, 600, 720, END):
            while b.time < at:
                me.run(1)
                if first is None and b.targets:
                    first = b.time
            g = b.g
            row = dict(t=at, stock=dict(g.stock), villagers=len(g.villagers), soldiers=sorted(g.soldiers.values()),
                       sites=[(s["name"], bool(s.get("done"))) for s in g.sites], owned=sorted(train.owned(g)),
                       pop=g.pop, targets=len(b.targets))
            rows.append(row)
            print(json.dumps(row), flush=True)
            if at == 600:
                game.command("tp aoe2mc 120 100 150 160 40")
                time.sleep(6)
                c.shot(os.path.join(out, "base.png"))
        print("first attack", first)
        if b.targets:
            p = g.positions(sorted(b.targets))
            if p:
                x, y, z = next(iter(p.values()))
                game.command(f"tp aoe2mc {x + 12} {y + 10} {z + 12} 135 35")
                time.sleep(6)
        c.shot(os.path.join(out, "attack.png"))
        print("p1 villagers alive", len(me.positions(sorted(me.villagers))))
        print("p1 villager list", len(me.villagers), "bot villager list", len(b.g.villagers))
        print("sidebar", me.shown)
