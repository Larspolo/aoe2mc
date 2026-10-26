"""Check of #934: a box selection (and a second click) of many units on Paper, with a real client. Usage: WORLD OUTDIR"""
import json, os, sys, time
ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import run, gather, combat, mc_shot  # noqa

world, out = sys.argv[1:3]
data = json.load(open(os.path.join(world, "aoe2mc.json")))
with run.Game(world) as g:
    g.forceload()
    combat.setup(g, data)
    G = gather.Gather(g, data).setup()
    with mc_shot.Client(g.game_port, g.version) as c:
        c.wait_join(lambda: "aoe2mc" in g.command("list"))
        time.sleep(5)
        g.command("gamemode spectator aoe2mc")
        names = {}
        for u, n in G.soldiers.items():
            names.setdefault(n, []).append(u)
        print({n: len(G.positions(us)) for n, us in names.items()})
        pos = G.positions(names["CHAMPION"] + names["HALBERDIER"])
        xs, zs = [p[0] for p in pos.values()], [p[2] for p in pos.values()]
        x0, x1, z0, z1 = int(min(xs)) - 1, int(max(xs)) + 1, int(min(zs)) - 1, int(max(zs)) + 1
        print("box", x0, z0, x1, z1)
        G.box("aoe2mc", (x0, z0))
        G.box("aoe2mc", (x1, z1))
        sel = sorted(G.selected)
        print("selected after box:", len(sel), {G.soldiers.get(u) for u in sel})
        print(g.command(f"execute if entity @e[tag={gather.SELECT}]"))
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        y = G.map.y(int(cx), int(cz)) or 70
        g.command(f"tp aoe2mc {cx} {y + 12} {z1 + 14} 180 35")
        time.sleep(10)
        c.shot(os.path.join(out, "box.png"))
        print({n: len(G.positions(us)) for n, us in names.items()})
        a = sorted(G.positions(names["LONGBOWMAN"]))[0]
        G.select(a)
        G.select_type(a)
        print("selected after second click:", len(G.selected), {G.soldiers.get(u) for u in G.selected})
        p = G.pos(a)
        g.command(f"tp aoe2mc {p[0]} {p[1] + 12} {p[2] + 14} 180 35")
        time.sleep(8)
        c.shot(os.path.join(out, "second_click.png"))
