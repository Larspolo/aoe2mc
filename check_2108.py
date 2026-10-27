"""Check of #2108 (after #2055): with real clicks of a client, the transport ship sails to the shore before the units
board it. The owner_loop map, `game/run.py W --play --cheats` on Paper in a subprocess, a mc_shot.Client. The client
right-clicks the 3 militia (each click adds it to the selection), then the own transport ship. Usage: WORLD OUTDIR"""
import json, math, os, queue, re, subprocess, sys, threading, time
ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, os.path.join(ROOT, "tools")]
import mc_shot  # noqa

world, out = sys.argv[1:3]
data = json.load(open(os.path.join(world, "aoe2mc.json")))
P1 = [o for o in data["objects"] if o["player"] == 1 and o["kind"] == "unit"]
SHIP = next(o["uuid"] for o in P1 if o["name"] == "TRANSPORT_SHIP")
MILITIA = [o["uuid"] for o in P1 if o["name"] == "MILITIA"]
ME = "aoe2mc"
res = {"ship": SHIP, "militia": MILITIA}
lines = queue.Queue()
log = open(os.path.join(out, "run.log"), "w")
p = subprocess.Popen([sys.executable, os.path.join(ROOT, "game/run.py"), world, "--play", "--cheats"],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                     cwd=ROOT, start_new_session=True)


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
        if m := re.search(pattern, ln):
            return m
    raise TimeoutError(pattern)


def cmd(text, pattern=None, s=10):
    while not lines.empty():
        lines.get()
    p.stdin.write(text + "\n")
    p.stdin.flush()
    return wait(pattern, s) if pattern else time.sleep(0.3)


def pos(u):
    m = cmd(f"data get entity {u} Pos", r"entity data: \[(-?[\d.]+)d, (-?[\d.]+)d, (-?[\d.]+)d\]")
    return tuple(round(float(v), 2) for v in m.groups())


def riders(u):
    m = cmd(f"execute as {u} on passengers if entity @s", r"Test (passed|failed)(?:\. Count: (\d+))?")
    return int(m[2] or 0)


def stand(x, y, z, yaw, pitch):
    """The player on a barrier block at (x, y, z), so the look does not change before the click (#1815)."""
    cmd(f"setblock {math.floor(x)} {math.floor(y) - 1} {math.floor(z)} minecraft:barrier")
    cmd(f"tp {ME} {x} {y} {z} {yaw:.1f} {pitch:.1f}")


def aim(target, back=4.0, up=2.0):
    """Stand north-west of the target position and look at its middle."""
    tx, ty, tz = target
    x, y, z = tx - back * 0.7, ty + up, tz - back * 0.7
    dx, dy, dz = tx - x, ty + 0.9 - (y + 1.62), tz - z
    yaw = math.degrees(math.atan2(-dx, dz))
    pitch = -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
    stand(x, y, z, yaw, pitch)
    time.sleep(1.5)


def overview(c, name):
    stand(52.5, 84, 124.5, 40, 38)                                     # north-east of the dock, high
    time.sleep(3)
    c.shot(os.path.join(out, name))


m = wait(r"Join the server localhost:(\d+) \(Minecraft ([\d.]+)", 400)
try:
    with mc_shot.Client(int(m[1]), m[2]) as c:
        end = time.time() + 120
        while ME not in cmd("list", r"players online.*")[0]:
            assert time.time() < end
            time.sleep(2)
        cmd(f"gamemode adventure {ME}")
        time.sleep(8)                                                  # the world is drawn, the chat toast goes
        res["start"] = {"ship": pos(SHIP), "militia": [pos(u) for u in MILITIA]}
        print("start", res["start"], flush=True)
        overview(c, "1-before.png")
        for u in MILITIA:                                              # a right click on each militia
            aim(pos(u))
            c.xdo("click", "3")
            time.sleep(1.5)
        res["glowing"] = cmd("execute if entity @e[nbt={Glowing:1b}]", r"Test (passed|failed).*")[0]
        c.shot(os.path.join(out, "2-selected.png"))
        aim(pos(SHIP), back=5, up=3)
        c.shot(os.path.join(out, "3-aim-ship.png"))
        n0 = res["riders0"] = riders(SHIP)                             # a crew can ride the ship already
        t0 = time.time()
        c.xdo("click", "3")                                            # a right click on the ship
        track, boarded = [], None
        shot = False
        while time.time() - t0 < 120:
            s, n = pos(SHIP), riders(SHIP)
            track.append({"t": round(time.time() - t0, 1), "ship": s, "riders": n,
                          "militia": [pos(u) for u in MILITIA]})
            if not shot and time.time() - t0 > 6:
                overview(c, "4-sailing.png")
                shot = True
            if n > n0 and boarded is None:
                boarded = track[-1]
            if boarded and n >= n0 + len(MILITIA) or boarded and time.time() - t0 > boarded["t"] + 30:
                break
            time.sleep(1)
        res["track"], res["boarded"] = track, boarded
        time.sleep(2)
        res["end"] = {"ship": pos(SHIP), "riders": riders(SHIP), "militia": [pos(u) for u in MILITIA]}
        overview(c, "5-after.png")
        res["chat"] = [ln for ln in c.text().splitlines() if "[CHAT]" in ln][-6:]
        print("end", res["end"], "boarded", boarded, flush=True)
finally:
    os.killpg(p.pid, 2)
    try:
        p.wait(120)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, 9)
    json.dump(res, open(os.path.join(out, "result.json"), "w"), indent=1, default=str)
print("done", flush=True)
