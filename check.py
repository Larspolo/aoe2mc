"""#3224: the converted scenario with objectives and a trigger victory, real order (play starts, the person joins late)."""
import contextlib, io, json, os, re, shutil, sys, threading, time
R = "/home/user/aoe2mc"
sys.path[:0] = [R, R + "/game", R + "/tools", R + "/tests"]
from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
import aoe2mc, mc_shot, scenarios
from game import run
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
START = {1: {"food": 321, "wood": 432, "gold": 543, "stone": 654}, 2: {"food": 111, "wood": 222, "gold": 333, "stone": 44}}
CAP = {1: 75, 2: 50}


def build(path):
    base = scenarios.triggers(path + ".base")
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(base)
    for i in (1, 2):
        p = scn.player_manager.players[i]
        for r, v in START[i].items():
            setattr(p, r, v)
        p.population_cap = CAP[i]
    scn.player_manager.players[2].human = False
    m = scn.message_manager
    m.instructions = "Bring the knight to the hill, then hold out."
    m.hints = "The hill is in the north-west."
    tm = scn.trigger_manager
    t = tm.triggers[1]
    t.display_as_objective, t.description, t.description_order = True, "Bring the knight to the hill.", 1
    t = tm.add_trigger("Victory", display_as_objective=True, description="Hold out for 75 seconds.", description_order=2)
    t.new_condition.timer(timer=75)
    t.new_effect.declare_victory(source_player=PlayerId.ONE)
    return scenarios.save(scn, path)


src = build(OUT + "/obj.aoe2scenario")
world = OUT + "/W"
shutil.rmtree(world, ignore_errors=True)
with contextlib.redirect_stdout(io.StringIO()):
    aoe2mc.convert(src, world)
data = json.load(open(world + "/aoe2mc.json"))
print("players", json.dumps({k: {x: v.get(x) for x in ("resources", "pop_limit", "computer")} for k, v in data["players"].items()}))
log = []
def note(s):
    log.append(s); print(s, flush=True)

with run.Game(world) as game:
    th = threading.Thread(target=run.play, args=(game, world), kwargs={"mode": "scenario", "wait": True, "seconds": 140},
                          daemon=True)
    th.start()
    t_start = time.time()
    time.sleep(20)                                                      # the person comes late
    with mc_shot.Client(game.game_port, game.version) as client:
        client.wait_join(lambda: "aoe2mc" in game.joined)
        t0 = time.time()
        note(f"join at {t0 - t_start:.1f} s after play()")
        g = game.g
        for h in run.savegame.sides(g) if hasattr(run, "savegame") else []:
            pass
        import savegame
        for h in savegame.sides(g):
            note(f"side p{h.player}: stock {h.stock} pop_limit {h.pop_limit} max_pop {__import__('train').max_pop(h)} mode {getattr(h, 'mode', None)} bot {type(h).__name__}")
        note(f"bots {[type(b).__name__ + ':p' + str(getattr(b, 'player', '?')) for b in getattr(g, 'bots', [])]}")
        seen = set()
        def poll():
            txt = client.text()
            for key in ("Welcome to the tiny map.", "A monastery stands now next to the hill.", "Bring the knight to the hill"):
                if key not in seen and key in txt:
                    seen.add(key); note(f"{time.time() - t0:5.1f} s chat: {key}")
        def until(sec):
            while time.time() - t0 < sec:
                poll(); time.sleep(0.3)
        until(4); client.shot(OUT + "/start0.png")
        until(6.5); client.shot(OUT + "/start_chat.png")
        until(10)
        if not os.environ.get("NOTP"): note(f"{time.time() - t0:5.1f} s tp knight: " + game.command("spreadplayers 18 18 0 1 false @e[type=minecraft:horse,tag=aoe2mc.p1,limit=1]"))
        until(14)
        note(f"monastery in g.buildings? {[b for b in map(str, getattr(g, 'targets', []) or [])][:0]}")
        if os.environ.get("NOTP"): client.key = client.click = client.shot = lambda *a, **k: None
        game.command("item replace entity aoe2mc hotbar.0 from entity aoe2mc inventory.26")
        time.sleep(0.5); client.key("1"); time.sleep(0.5); client.click(client.size[0] // 2, client.size[1] // 2, 3)
        time.sleep(2); client.shot(OUT + "/instructions.png")
        client.key("Page_Down"); time.sleep(1.5); client.shot(OUT + "/objectives.png")
        client.key("Page_Down"); time.sleep(1.5); client.shot(OUT + "/hints.png")
        client.key("Escape")
        arch = lambda: game.command("execute if entity @e[type=minecraft:skeleton,tag=aoe2mc.p2]")
        note(f"{time.time() - t0:5.1f} s archers: {arch()}")
        gone = None
        while time.time() - t0 < 120 and not g.ended:
            poll()
            if gone is None and "count" not in arch().lower():
                gone = time.time() - t0; note(f"{gone:5.1f} s archer gone")
            time.sleep(0.5)
        note(f"{time.time() - t0:5.1f} s ended: {g.ended}")
        time.sleep(2); mc_shot.Client.shot(client, OUT + "/victory.png")
        for h in savegame.sides(g):
            note(f"end p{h.player}: ended {h.ended}")
        time.sleep(3)
        problems = [l for l in game.server.log if re.search(r"Unknown or incomplete command|Incorrect argument|ERROR|Exception", l)]
        note(f"problems {len(problems)}: {problems[:8]}")
        open(OUT + "/client.txt", "w").write(client.text())
open(OUT + "/server.txt", "w").write("\n".join(game.server.log))
open(OUT + "/notes.txt", "w").write("\n".join(log))
