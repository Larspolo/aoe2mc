"""Screenshot of the pointing mark (#989): a real client looks at an enemy unit 40 blocks away."""
import json, math, os, sys, time
ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, ROOT + "/tools", ROOT + "/game"]
import gather, hints, run, mc_shot
world, out = sys.argv[1], sys.argv[2]
data = json.load(open(os.path.join(world, "aoe2mc.json")))
with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
    client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
    game.forceload()
    time.sleep(5)
    g = gather.Gather(game, data).setup()
    soldier = sorted(g.soldiers)[0]
    g.select(soldier)
    places = g.places()
    foes = sorted(u for u in g.enemies if u in places)
    e = foes[len(foes) // 2]
    x, y, z = places[e]
    for dx, dz in ((0, -40), (0, 40), (-40, 0), (40, 0)):
        px, pz = x + dx, z + dz
        if g.map.y(int(px), int(pz)) is not None:
            break
    py = g.map.y(int(px), int(pz)) + 4
    eye = (px, py + 1.62, pz)
    v = (x - eye[0], y + 1 - eye[1], z - eye[2])
    yaw, pitch = math.degrees(math.atan2(-v[0], v[2])), -math.degrees(math.atan2(v[1], math.hypot(v[0], v[2])))
    game.command("gamemode spectator aoe2mc")
    game.command(f"tp aoe2mc {px} {py} {pz} {yaw:.2f} {pitch:.2f}")
    time.sleep(4)
    for i in range(16):
        g.point()
        hints.tick(g)
        if i == 15:
            client.shot(out)
        time.sleep(0.25)
    print("enemy", e, places[e], "player", (px, py, pz), "dist", math.dist((px, pz), (x, z)), "pointing", g.pointing)
