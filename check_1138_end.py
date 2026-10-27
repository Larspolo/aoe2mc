"""Check 5 of #1138 (after #2051): the server of a play game stays up after the end, and the fog of war goes.
Game A: the real `game/run.py W --play --cheats --bot` in a subprocess, a real client types "torpedo2". Expected: the
"Victory" title, the line "The game ended (Victory). The server stays up", the client stays on the server 40 s later.
Game B: a wonder victory (timer cut to 20 s) with enemy villagers out of sight. Expected: hidden before the end,
visible after run.unveil (the tail of run.play). Usage: OUTDIR"""
import contextlib, io, json, os, queue, re, shutil, subprocess, sys, threading, time
ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import aoe2mc, scenarios, run, gather, combat, mc_shot, build, fog  # noqa
from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.units import UnitInfo

out = sys.argv[1]
P1, P2 = scenarios.PlayerId.ONE, scenarios.PlayerId.TWO
scn = scenarios.new_scenario(48)
um = scn.unit_manager
um.add_unit(P1, BuildingInfo.TOWN_CENTER.ID, x=10, y=10)
um.add_unit(P1, UnitInfo.VILLAGER_MALE.ID, x=14.5, y=7.5)
um.add_unit(P2, BuildingInfo.TOWN_CENTER.ID, x=38, y=38)
for i in range(4):
    um.add_unit(P2, UnitInfo.VILLAGER_MALE.ID, x=34.5 + i, y=33.5)
src, base = os.path.join(out, "end.aoe2scenario"), os.path.join(out, "W0")
scenarios.save(scn, src)
shutil.rmtree(base, ignore_errors=True)
with contextlib.redirect_stdout(io.StringIO()):
    aoe2mc.convert(src, base)
data = json.load(open(os.path.join(base, "aoe2mc.json")))
tcs = {o["player"]: (o["footprint"][0] + 1, o["footprint"][1] + 1) for o in data["objects"]
       if o["kind"] == "building" and o["name"] == "TOWN_CENTER"}
ME = "aoe2mc"
res = {}


def copy(name):
    world = os.path.join(out, name)
    shutil.rmtree(world, ignore_errors=True)
    shutil.copytree(base, world)
    return world


def say(c, text):
    c.key("t")
    time.sleep(1)
    c.xdo("type", "--delay", 50, text)
    c.key("Return")
    time.sleep(1)


def shots(c, name):
    for i, w in enumerate((0, 0.5, 1.0)):                             # the title fades in and out in about 4 s
        time.sleep(w)
        c.shot(os.path.join(out, f"{name}-{i}.png"))


# Game A: the real program
ONLY_B = os.environ.get("ONLY_B")
world = copy("WA")
lines = queue.Queue()
p = subprocess.Popen([sys.executable, os.path.join(ROOT, "game/run.py"), world, "--play", "--cheats", "--bot"],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                     cwd=ROOT, start_new_session=True)
log = open(os.path.join(out, "5-run.log"), "a")


def pump():
    for ln in p.stdout:
        log.write(ln)
        log.flush()
        lines.put(ln)
threading.Thread(target=pump, daemon=True).start()


def wait(pattern, s):
    end = time.time() + s
    while time.time() < end:
        try:
            ln = lines.get(timeout=1)
        except queue.Empty:
            continue
        m = re.search(pattern, ln)
        if m:
            return m
    raise TimeoutError(pattern)


def cmd(text, pattern=None, s=10):
    p.stdin.write(text + "\n")
    p.stdin.flush()
    return wait(pattern, s) if pattern else None


m = None if ONLY_B else wait(r"Join the server localhost:(\d+) \(Minecraft ([\d.]+)", 400)
try:
    assert not ONLY_B
    port, version = int(m[1]), m[2]
    with mc_shot.Client(port, version) as c:
        end = time.time() + 120
        while ME not in cmd("list", r"players online.*", 10)[0]:
            assert time.time() < end
            time.sleep(2)
        cmd(f"gamemode adventure {ME}")
        x, z = tcs[2]
        cmd(f"spreadplayers {x} {z + 20} 0 1 false {ME}")      # on the ground: no fall
        cmd(f"execute as {ME} at @s run tp @s ~ ~ ~ 180 20")
        time.sleep(15)                                                 # the bot starts, the chat toast goes
        c.shot(os.path.join(out, "5-a-before.png"))
        say(c, "torpedo2")
        t0 = time.time()
        m = wait(r"The game ended \((\w+)\)\. The server stays up", 60)
        res["a"] = {"ended": m[1], "s": round(time.time() - t0, 1)}
        shots(c, "5-a-victory")
        time.sleep(40)
        p.stdin.write("list\n")
        p.stdin.flush()
        time.sleep(3)
        res["a"]["alive"] = p.poll() is None
        res["a"]["list"] = open(os.path.join(out, "5-run.log")).read().splitlines()[-3:]
        cmd(f"spreadplayers {tcs[1][0]} {tcs[1][1] + 20} 0 1 false {ME}")       # the player can still move around
        time.sleep(4)
        c.shot(os.path.join(out, "5-a-after.png"))
        res["a"]["chat"] = [ln for ln in c.text().splitlines() if "[CHAT]" in ln][-5:]
        res["a"]["client_lost"] = "Disconnected" in c.text() or "Connection Lost" in c.text()
        print("a", json.dumps(res["a"]), flush=True)
except AssertionError:
    pass
finally:
    os.killpg(p.pid, 2)                                                # Ctrl-C stops it
    try:
        p.wait(120)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, 9)
    res.setdefault("a", {})["rc"] = p.returncode

# Game B: wonder victory, fog before and after
with run.Game(copy("WB")) as game:
    game.forceload()
    end = time.time() + 60
    while True:
        g = gather.Gather(game, data, cheats=True).setup()
        if g.villagers:
            break
        assert time.time() < end
        time.sleep(1)
    combat.setup(game, data)
    for r, n in build.COSTS["WONDER"].items():
        g.stock[r] += n
        game.command(f"scoreboard players add {r.capitalize()} {g.board} {n}")
    with mc_shot.Client(game.game_port, game.version) as c:
        c.wait_join(lambda: ME in game.command("list"))
        game.command(f"gamemode adventure {ME}")
        rect = build.near(g, "WONDER", tcs[1], reach=30)
        site = build.found(g, "WONDER", rect)
        build.rise(g, site, build.BUILD_TIMES["WONDER"])
        g.run(10, until=lambda: vars(g).get("wonders"))
        g.run(4)
        vs = [o for o in data["objects"] if o["kind"] == "unit" and o["player"] == 2]
        x = sum(o["tile"][0] for o in vs) / len(vs) * 4
        z = sum(o["tile"][1] for o in vs) / len(vs) * 4
        game.command(f"tp {ME} {x:.1f} {g.map.y(int(x), int(z) - 10) + 4} {z - 10:.1f} 0 20")   # north of them
        time.sleep(6)
        c.shot(os.path.join(out, "5-b-fog.png"))
        res["b"] = {"hidden_before": len(vars(g).get("fog", {}).get("hidden", ())), "reveal_before": g.reveal}
        for t in g.wonders.values():
            t["left"] = 20.0                                           # cut the 1000 game seconds to 20
        g.run(60, until=lambda: g.ended)
        run.unveil(g)                                                  # the tail of run.play (#2051)
        shots(c, "5-b-victory")
        time.sleep(4)
        c.shot(os.path.join(out, "5-b-after.png"))
        res["b"] |= {"ended": g.ended, "reveal_after": g.reveal,
                     "hidden_after": len(vars(g).get("fog", {}).get("hidden", ())),
                     "p2_alive": game.command("execute if entity @e[tag=aoe2mc.p2]")}
        print("b", json.dumps(res["b"]), flush=True)
json.dump(res, open(os.path.join(out, "5-result.json"), "w"), indent=1, default=str)
print("done", flush=True)
