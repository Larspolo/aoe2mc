"""Check of #823: fights of military units on Paper, through the player functions of game/gather.py."""
import json, math, os, re, shutil, sys, time
R = "/home/user/aoe2mc"
sys.path[:0] = [R, R + "/game", R + "/tools", R + "/tests"]
import gather, combat, mc_shot  # noqa
from game import run  # noqa

S = sys.argv[1]
world = shutil.copytree(S + "/battleW", S + "/battleW_run", dirs_exist_ok=False)
data = json.load(open(world + "/aoe2mc.json"))
res = {"pairs": [], "notes": []}


def uuids(name, player):
    return [o["uuid"] for o in data["objects"] if o.get("uuid") and o["name"] == name and o["player"] == player]


with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
    client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
    game.forceload()
    for _ in range(60):
        g = gather.Gather(game, data).setup()
        if len(g.villagers) == len(g.units):
            break
        time.sleep(1)
    print("stats set:", combat.setup(game, data), flush=True)
    game.command("gamemode spectator aoe2mc")
    game.command("time set noon")
    game.command("gamerule advance_time false")

    def health(u):
        out = game.command(f"data get entity {u} Health")
        m = re.search(r"(-?[\d.]+)f", out)
        return float(m.group(1)) if m and "has the following" in out else None

    def ground(x, z):
        return int(g.map.y(int(x), int(z)))

    def look(eye, at):
        """tp the player so that its eye is at eye and it looks at the point at (tp facing aims from the feet)."""
        dx, dy, dz = (at[i] - eye[i] for i in range(3))
        yaw, pitch = math.degrees(math.atan2(-dx, dz)), -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
        game.command(f"tp aoe2mc {eye[0]} {eye[1] - 1.62} {eye[2]} {yaw:.3f} {pitch:.3f}")

    def aim_click(eye, target):
        """Stand at eye and look at the target's chest, then the same click as a right click of the player."""
        p = g.pos(target)
        look(eye, (p[0], p[1] + 1.0, p[2]))
        time.sleep(0.3)
        me = g.pos("aoe2mc")
        rot = game.command("data get entity aoe2mc Rotation")
        eye2 = (me[0], me[1] + 1.62, me[2])
        d = gather.direction(*map(float, re.findall(gather.NUMBER, rot.rsplit(":", 1)[-1])))
        units = {k: v.pos for k, v in g.villagers.items()} | g.positions(list(g.soldiers) + list(g.enemies))
        print("aim", target, "me", me, "rot", rot[-40:], "target at", p, "pick", gather.pick_unit(eye2, d, units), flush=True)
        g.click("aoe2mc")

    X, Z = 40, 128
    keep = {uuids(a, 1)[0] for a in ("CHAMPION", "CAVALIER", "LONGBOWMAN", "ARBALESTER")} | set(uuids("CHAMPION", 1)[1:4]) \
        | {uuids(t, 2)[0] for t in ("TWO_HANDED_SWORDSMAN", "CROSSBOWMAN", "PIKEMAN", "ELITE_SKIRMISHER")}
    for o in data["objects"]:                            # a clean field: only the units of the check
        if o["kind"] == "unit" and o.get("uuid") and o["uuid"] not in keep:
            game.command(f"kill {o['uuid']}")
    time.sleep(1)
    pairs = [("CHAMPION", "TWO_HANDED_SWORDSMAN", 24), ("CAVALIER", "CROSSBOWMAN", 32),
             ("LONGBOWMAN", "PIKEMAN", 32), ("ARBALESTER", "ELITE_SKIRMISHER", 32)]
    only = os.environ.get("ONLY")
    for k, (a_name, t_name, gap) in enumerate(pairs):
        if only and a_name != only:
            continue
        a, t = uuids(a_name, 1)[0], uuids(t_name, 2)[0]
        game.command(f"tp {a} {X + 0.5} {ground(X, Z)} {Z + 0.5} 180 0")
        game.command(f"tp {t} {X + 0.5} {ground(X, Z + gap)} {Z + gap + 0.5} 0 0")
        time.sleep(1.5)
        ha0, ht0 = health(a), health(t)
        # select: a click on the own unit, then a click on the enemy (the attack order)
        aim_click((X + 6.5, ground(X, Z) + 3, Z - 4.5), a)
        sel = a in g.selected and "Test passed" in game.command(f"execute if entity @e[tag={gather.SELECT}]")
        aim_click((X + 6.5, ground(X, Z) + 3, Z + gap / 2), t)
        t0, hits_t, hits_a, first, times_t = time.time(), [ht0], [ha0], None, []
        shot = False
        while time.time() - t0 < 60:
            ht, ha = health(t), health(a)
            if ht is not None and ht != hits_t[-1]:
                hits_t.append(ht)
                times_t.append(round(time.time() - t0, 2))
                if first is None:
                    pa, pt = g.pos(a), g.pos(t)
                    first = round(math.dist((pa[0], pa[2]), (pt[0], pt[2])), 1) if pa and pt else None
            if only:
                pa, pt = g.pos(a), g.pos(t)
                print("t", round(time.time() - t0, 1), "a", pa and [round(c, 1) for c in pa], "t", pt and [round(c, 1) for c in pt], ht, ha,
                      game.command(f"data get entity {t} Motion")[-40:], flush=True)
            if ha is not None and ha != hits_a[-1]:
                hits_a.append(ha)
            if not shot and len(hits_t) >= 2 and k in (0, 1):
                pa = g.pos(a)
                game.command(f"tp aoe2mc {pa[0] + 5} {pa[1] + 2.5} {pa[2] + 1} facing entity {a} feet")
                time.sleep(0.6)
                client.shot(f"{S}/check/fight_{a_name.lower()}.png")
                shot = True
            if ht is None or ha is None:
                break
            time.sleep(0.05)
        drops = lambda h: [round(x - y, 1) for x, y in zip(h, h[1:]) if x is not None and y is not None]
        res["pairs"].append({"attacker": a_name, "target": t_name, "selected": sel, "target_hp": hits_t,
                             "attacker_hp": hits_a, "times_t": times_t, "per_hit_target": drops(hits_t), "per_hit_attacker": drops(hits_a),
                             "dist_first_hit": first, "target_dead": health(t) is None,
                             "expected_per_hit": combat.damage(a_name, t_name),
                             "expected_back": combat.damage(t_name, a_name)})
        print(res["pairs"][-1], flush=True)
        for u in (a, t):
            game.command(f"kill {u}")
        time.sleep(1)

    if only:
        raise SystemExit
    # a building: 3 champions next to the stable of player 2, selected and sent with clicks
    stable = next(o for o in data["objects"] if o["name"] == "STABLE" and o["player"] == 2)
    fort = combat.target_uuid(stable["footprint"])
    x0, z0, x1, z1 = stable["footprint"]
    champs = uuids("CHAMPION", 1)[1:4]
    for i, c in enumerate(champs):
        cx, cz = (x0 + x1) // 2 - 2 + 2 * i, z1 + 4
        game.command(f"tp {c} {cx + 0.5} {ground(cx, cz)} {cz + 0.5} 180 0")
    time.sleep(1.5)
    hp = lambda: (int(m.group(1)) if (m := re.search(r"has (-?\d+) ", game.command(f"scoreboard players get {fort} aoe_hp"))) else None)
    eye = ((x0 + x1) / 2 + 0.5, ground((x0 + x1) // 2, z1 + 10) + 4, z1 + 12.5)
    for c in champs:
        aim_click(eye, c)
    selected = len(g.selected & set(champs))
    p = (eye[0], eye[1], eye[2])
    look(p, ((x0 + x1) / 2, ground(x0, z0) + 2, z1 - 0.5))
    time.sleep(0.3)
    g.click("aoe2mc")
    seen, t0, shot, when = [hp()], time.time(), False, []
    while time.time() - t0 < 40:
        h = hp()
        if h != seen[-1]:
            seen.append(h)
            when.append(round(time.time() - t0, 2))
        if not shot and len(seen) >= 4:
            look(((x0 + x1) / 2 + 9.5, ground(x0, z0) + 9, z1 + 16.5), ((x0 + x1) / 2, ground(x0, z0) + 2, (z0 + z1) / 2))
            time.sleep(0.8)
            client.shot(f"{S}/check/building.png")
            shot = True
        time.sleep(0.1)
    res["building"] = {"name": "STABLE", "selected": selected, "sieged": fort in g.sieged, "hp": seen, "times": when,
                       "expected_per_hit": combat.damage("CHAMPION", "STABLE")}
    print(res["building"], flush=True)
    bad = re.findall(r".*(?:ERROR|Exception).*", open(game.folder + "/logs/latest.log").read())
    res["log_errors"] = bad[:10]
json.dump(res, open(S + "/check/result.json", "w"), indent=1)
