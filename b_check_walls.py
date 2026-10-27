"""Check of #1327 (second): walls and gates of the game program on Paper with a real client, with the clicks of the
player (build menu score + a look at the ground + Gather.click): the selected villagers build at once (#1654), a
straight gate and a diagonal gate (#1655), the portcullis (#1656), the own unit through the gate, the enemy not, and
Fortified Wall. Map: owner_loop (48 x 48). Usage: OUTDIR"""
import contextlib, io, json, math, os, shutil, sys, time
ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import aoe2mc, scenarios, run, gather, combat, build, train, mc_shot  # noqa

out = sys.argv[1]
src, world = os.path.join(out, "loop.aoe2scenario"), os.path.join(out, "W")
scenarios.owner_loop(src)
shutil.rmtree(world, ignore_errors=True)
with contextlib.redirect_stdout(io.StringIO()):
    aoe2mc.convert(src, world)
data = json.load(open(os.path.join(world, "aoe2mc.json")))
res, ME = {}, "aoe2mc"


def log(k, v):
    res[k] = v
    print(k, json.dumps(v, default=str), flush=True)


with run.Game(world) as game:
    game.forceload()
    end = time.time() + 60
    while True:
        g = gather.Gather(game, data, cheats=True).setup()
        if g.villagers:
            break
        assert time.time() < end
        time.sleep(1)
    combat.setup(game, data)
    T = g.map.T
    for r in g.stock:
        g.stock[r] += 5000
    for r in gather.RESOURCES:
        game.command(f"scoreboard players set {r} {g.board} {g.stock[r.lower()]}")   # the sidebar shows the new stock
    g.techs |= {"FEUDAL_AGE"}
    log("locked", build.locked(g, "STONE_WALL"))
    enemy = next(o["uuid"] for o in data["objects"] if o["kind"] == "unit" and o["player"] == 2 and o["name"] == "MILITIA")

    def click(name, tile):
        x, z = tile[0] * T + T // 2, tile[1] * T + T // 2
        y = g.map.y(x, z) or 64
        game.command(f"scoreboard players set {ME} {build.OBJECTIVE} {build.MENU.index(name) + 1}")
        game.command(f"tp {ME} {x + 0.5} {y + 12} {z + 0.5} 0 90")
        time.sleep(0.5)
        n, before = len(g.sites), {id(s) for s in g.sites}
        look = g.look(ME)
        print("click", name, tile, "eye", [round(a, 1) for a in look[0]] if look else None,
              "cell", g.map.pick_ground(*look) if look else None, flush=True)
        g.click(ME)
        game.command(f"tp {ME} 40.5 {(g.map.y(40, 20) or 64) + 2} 20.5")         # away from the walls: no suffocation
        return [s for s in g.sites if id(s) not in before]

    def finish(sites, limit=900):
        t0 = g.clock()
        while not all(s["progress"] >= 1 for s in sites) and g.clock() - t0 < limit:
            g.run(5)
        return round(g.clock() - t0), sum(s["progress"] >= 1 for s in sites), len(sites)

    def builders(site):
        return sorted(v.state for v in g.villagers.values() if v.site is site)

    def shot(name, at, look=(45, 40)):
        game.command(f"tp {ME} {at[0]:.1f} {at[1]:.1f} {at[2]:.1f} {look[0]} {look[1]}")
        time.sleep(4)
        c.shot(os.path.join(out, name))

    with mc_shot.Client(game.game_port, game.version) as c:
        c.wait_join(lambda: ME in game.command("list"))
        game.command(f"gamemode adventure {ME}")
        game.command(f"effect give {ME} resistance infinite 4 true")      # no fall or suffocation death
        g.selected = set(g.villagers)
        log("villagers", len(g.selected))
        click("PALISADE_WALL", (24, 6))
        line = click("PALISADE_WALL", (30, 6))
        log("palisade", dict(sites=len(line), builders=builders(line[0]) if line else None))
        log("palisade done", finish(line))
        click("STONE_WALL", (2, 20))
        stone = click("STONE_WALL", (45, 20))
        log("stone", dict(sites=len(stone), builders=builders(stone[0]) if stone else None))
        log("stone done", finish(stone, 1800))
        gate = click("GATE", (25, 20))
        log("gate", dict(sites=[(s["name"], s["footprint"]) for s in gate], builders=builders(gate[0]) if gate else None))
        log("gate done", finish(gate))
        click("STONE_WALL", (14, 24))
        diag = click("STONE_WALL", (20, 30))
        log("diag", dict(sites=len(diag), builders=builders(diag[0]) if diag else None))
        log("diag done", finish(diag))
        dgate = click("GATE", (17, 27))
        log("diag gate", dict(sites=[(s["name"], s["footprint"]) for s in dgate]))
        log("diag gate done", finish(dgate))
        y = g.map.y(26 * T, 20 * T) or 64
        shot("1_palisade.png", (27 * T, y + 10, 6 * T + 12), (180, 35))
        x0, x1, z0, z1 = gate[0]["footprint"]
        gx, gz = (x0 + x1) / 2, (z0 + z1) / 2
        shot("2_stone_gate.png", (gx, y + 6, gz - 12), (0, 25))
        bars = lambda: all("passed" in game.command(f"execute if block {math.floor(gx) + dx} {y + 1} {math.floor(gz)} minecraft:iron_bars") for dx in (-1, 0))
        log("bars closed", bars())
        # the own villager from the north through the gate, then the enemy militia from the south
        v = min(g.villagers, key=lambda u: math.dist(g.villagers[u].pos[::2], (gx, gz - 8)))
        game.command(f"tp {v} {gx} {y} {gz - 8}")                  # north of the wall
        time.sleep(1)
        log("own start", g.positions([v]).get(v))
        game.command(f"aoe moveto {v} {gx} {y} {gz + 18}")
        t0, opened, p = time.time(), False, None
        while time.time() - t0 < 40:
            opened |= not bars()
            p = g.positions([v]).get(v)
            if p and p[2] > gz + 16:
                break
            time.sleep(0.3)
        log("own", dict(pos=p, opened=opened, through=bool(p and p[2] > gz + 3)))
        shot("3_gate_open.png", (gx, y + 6, gz - 12), (0, 25)) if not bars() else None
        game.command(f"tp {ME} 40.5 {(g.map.y(40, 20) or 64) + 2} 20.5")
        t0 = time.time()
        while time.time() - t0 < 20 and not bars():
            time.sleep(0.5)
        log("bars closed after", dict(closed=bars(), seconds=round(time.time() - t0, 1)))
        game.command(f"tp {enemy} {gx} {y} {gz + 12}")
        game.command(f"aoe moveto {enemy} {gx} {y} {gz - 10}")
        time.sleep(20)
        p = g.positions([enemy]).get(enemy)
        log("enemy", dict(pos=p, stays=bool(p and p[2] > gz), bars=bars()))
        dx0, dx1, dz0, dz1 = dgate[0]["footprint"] if dgate else (0, 0, 0, 0)
        shot("4_diagonal_gate.png", ((dx0 + dx1) / 2 + 8, y + 8, (dz0 + dz1) / 2 - 8), (45, 35))
        def top(x, z):                                                 # the highest solid block of the column
            return max([h for h in range(y, y + 14) if "passed" not in game.command(f"execute if block {x} {h} {z} minecraft:air")], default=None)
        cols = [(60, 82), (61, 82), (gx - 1, gz - 1)]
        log("wall top before", [top(math.floor(a), math.floor(b)) for a, b in cols])
        g.techs |= {"CASTLE_AGE"}
        train.research(g, {"name": "FORTIFIED_WALL", "player": ME})
        g.run(30)
        log("wall top after", [top(math.floor(a), math.floor(b)) for a, b in cols])
        shot("5_fortified.png", (gx, y + 6, gz - 12), (0, 25))
        shot("6_fortified_side.png", (gx + 30, y + 10, gz - 14), (60, 20))
json.dump(res, open(os.path.join(out, "result.json"), "w"), indent=1, default=str)
print("done")
