"""Check of #1108: the four AoE2 stances of the military units on Paper (game/run.py --play setup), with a real
client. The stance input goes through stance.open_menu and the menu click, as the player input. One lane for each
stance and unit (militia, archer, scout cavalry of player 1); an enemy militia of player 2 (no attack, 1000 hit
points) walks into the sight, away, and next to the unit. Usage: OUTDIR"""
import contextlib, io, json, math, os, re, shutil, sys, time, urllib.parse
ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import aoe2mc, scenarios, run, gather, combat, stance, mc_shot  # noqa
from AoE2ScenarioParser.datasets.units import UnitInfo

out = sys.argv[1]
P1, P2 = scenarios.PlayerId.ONE, scenarios.PlayerId.TWO
STANCES = [s for s, *_ in stance.ITEMS]
KINDS = ("MILITIA", "ARCHER", "SCOUT_CAVALRY")
XS = [6.5 + 15 * s for s in range(4)]                  # tile x of a stance column: 60 blocks apart
YS = [6.5 + 20 * k for k in range(3)]                  # tile y of a unit row: 80 blocks apart
scn = scenarios.new_scenario(64)
scn.player_manager.active_players = 2
um = scn.unit_manager
south = math.pi / 2
for s, x in enumerate(XS):
    for k, y in enumerate(YS):
        um.add_unit(P1, getattr(UnitInfo, KINDS[k]).ID, x=x, y=y, rotation=south)
        um.add_unit(P2, UnitInfo.MILITIA.ID, x=x, y=y + 10, rotation=south + math.pi)
src, world = os.path.join(out, "stances.aoe2scenario"), os.path.join(out, "W")
scenarios.save(scn, src)
shutil.rmtree(world, ignore_errors=True)
with contextlib.redirect_stdout(io.StringIO()):
    aoe2mc.convert(src, world)
data = json.load(open(os.path.join(world, "aoe2mc.json")))
units = [o for o in data["objects"] if o["kind"] == "unit" and o.get("uuid")]
T = data.get("tile_size", 4)


def lane(o):
    return min(range(4), key=lambda s: abs(o["tile"][0] - XS[s])), min(range(3), key=lambda k: abs(o["tile"][1] - YS[k] - 5))


own = {lane(o): o["uuid"] for o in units if o["player"] == 1}
foe = {lane(o): o["uuid"] for o in units if o["player"] == 2}
assert len(own) == 12 and len(foe) == 12, (own, foe)
ME = "aoe2mc"


def pos(u):
    r = game.command(f"data get entity {u} Pos")
    v = re.findall(r"(-?[\d.]+)d", r)
    return tuple(map(float, v[:3])) if v else None


def health(u):
    m = re.search(r"([\d.]+)f", game.command(f"data get entity {u} Health"))
    return float(m[1]) if m else None


def flat(a, b):
    return round(math.hypot(a[0] - b[0], a[2] - b[2]), 1)


def walk(fn, secs):
    """Order each enemy with fn(lane, own position, enemy position) -> (x, z), then poll for secs: the farthest
    distance of each own unit from its start, its last distance, and the hit points of the enemy."""
    for key, u in foe.items():
        x, z = fn(key, pos(own[key]), pos(u))
        game.command(f"aoe moveto {u} {x} {post[key][1]} {z}")
    far = {k: 0.0 for k in own}
    end = time.time() + secs
    while time.time() < end:
        for k, u in own.items():
            p = pos(u)
            if p:
                far[k] = max(far[k], flat(p, post[k]))
        time.sleep(0.5)
    return {k: {"far": far[k], "now": flat(pos(own[k]) or post[k], post[k]), "foe_hp": health(foe[k]),
                "gap": flat(pos(own[k]) or post[k], pos(foe[k]) or post[k])} for k in own}


rows = {}
with run.Game(world) as game:
    game.forceload()
    end = time.time() + 60
    while True:
        g = gather.Gather(game, data, cheats=True).setup()
        if g.soldiers:
            break
        assert time.time() < end
        time.sleep(1)
    combat.setup(game, data)
    for u in foe.values():                                           # the enemies only walk and take the hits
        game.command(combat.stance_command(u, "no_attack"))
        game.command(f"aoe stats {u} 1000 0 0 0 0 infantry -")
    print("teams", game.command("team list"), flush=True)
    with mc_shot.Client(game.game_port, game.version) as c:
        c.wait_join(lambda: ME in game.command("list"))
        game.command(f"gamemode spectator {ME}")
        game.command("time set noon")
        time.sleep(10)                                               # the toasts of the join go away
        for s, name in enumerate(STANCES):                          # the player input: the stance menu of a selection
            g.selected = {own[(s, k)] for k in range(3)}
            stance.open_menu(g, ME, own[(s, 0)])
            if s == 2:
                p = pos(own[(s, 0)])
                game.command(f"tp {ME} {p[0]} {p[1] + 3} {p[2] - 6} 0 20")
                time.sleep(4)
                c.shot(os.path.join(out, "menu.png"))
            g.menus[ME](ME, s, False)
        got = {f"{s},{k}": game.command(f"aoe stance {own[(s, k)]}").strip() for s in range(4) for k in range(3)}
        print("stances", json.dumps(got), flush=True)
        time.sleep(5)
        post = {k: pos(u) for k, u in own.items()}
        start_hp = {k: health(u) for k, u in foe.items()}
        # 1: the enemy walks to 3 tiles (12 blocks) in front of the unit: in the sight of all, in the range of the archer
        rows["near"] = walk(lambda k, p, f: (post[k][0], post[k][2] + 3 * T), 15)
        print("near", json.dumps({f"{k}": v for k, v in rows["near"].items()}), flush=True)
        p = post[(1, 0)]
        game.command(f"tp {ME} {p[0] + 10} {p[1] + 6} {p[2] + 6} 90 25")
        time.sleep(3)
        c.shot(os.path.join(out, "fight.png"))
        # 2: the enemy walks away, 12 tiles (48 blocks) from the place of the unit
        rows["away"] = walk(lambda k, p, f: (post[k][0], post[k][2] + 12 * T), 25)
        print("away", json.dumps({f"{k}": v for k, v in rows["away"].items()}), flush=True)
        # 3: the enemy walks next to the unit and hits it once
        hp3 = {k: health(u) for k, u in foe.items()}
        rows["next"] = walk(lambda k, p, f: (p[0], p[2] + 1.5), 16)
        for k, u in foe.items():
            game.command(f"damage {own[k]} 1 minecraft:mob_attack by {u}")
        r = walk(lambda k, p, f: (f[0], f[2]), 8)
        for k in own:
            rows["next"][k]["foe_hp"], rows["next"][k]["foe_hp0"] = r[k]["foe_hp"], hp3[k]
            rows["next"][k]["far_after_hit"] = r[k]["far"]
        print("next", json.dumps({f"{k}": v for k, v in rows["next"].items()}), flush=True)
        json.dump({"stances": got, "start_hp": {f"{k}": v for k, v in start_hp.items()},
                   "rows": {ph: {f"{STANCES[k[0]]}/{KINDS[k[1]]}": v for k, v in r.items()} for ph, r in rows.items()}},
                  open(os.path.join(out, "result.json"), "w"), indent=1)
        log = open(os.path.join(world, "logs", "latest.log")).read() if os.path.exists(os.path.join(world, "logs", "latest.log")) else ""
        print("errors", [ln for ln in log.splitlines() if "ERROR" in ln or "Exception" in ln][:10], flush=True)
