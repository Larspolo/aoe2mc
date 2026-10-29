import json, sys, time
sys.path[:0] = ["/home/user/aoe2mc", "/home/user/aoe2mc/tools", "/home/user/aoe2mc/game"]
import mc_shot
from game import combat, run, gather, stance, demolish, menu, ruins
W, D = sys.argv[1], sys.argv[2]
data = json.load(open(f"{W}/aoe2mc.json"))
def rows(items): return max(i[0] for i in items) // 9 + 1
with run.Game(W) as game, mc_shot.Client(game.game_port, game.version) as client:
    client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
    time.sleep(5)
    game.forceload()
    combat.setup(game, data)
    g = gather.Gather(game, data).setup()
    print("paper", g.paper)
    print('soldiers', len(g.soldiers)); v = sorted(g.soldiers)[:3]
    g.choose(set(v), v[0])
    print("pick", client.pick(g, v[0]))
    print("clicks", g.clicks()); time.sleep(2)
    print("direct", menu.show.__module__, stance.open_menu(g, "aoe2mc", v[0])); time.sleep(2)
    client.shot(f"{D}/1-unit-menu.png")
    print("open menus", getattr(g, "menus", None) and list(g.menus)[:3])
    pos0 = g.positions(v)
    print("before", pos0)
    client.click(*client.slot(stance.DELETE, rows(stance.items(g, v[0]))))
    time.sleep(1); menu.clicks(g); time.sleep(2)
    print("after", g.positions(v), "selected", g.selected)
    print("alive", {u: "has the following" in game.command(f"data get entity {u} Health") or game.command(f"data get entity {u} Health") for u in v})
    game.command(f"tp aoe2mc {pos0[v[0]][0]:.1f} {pos0[v[0]][1]+6:.1f} {pos0[v[0]][2]:.1f} facing {pos0[v[0]][0]:.1f} {pos0[v[0]][1]:.1f} {pos0[v[0]][2]+0.1:.1f}")
    time.sleep(3); client.shot(f"{D}/2-units-after.png")
    own = ruins.own(g)
    rects = sorted(own.values())
    rect = next((r for r in rects if demolish.name(g, r) == "HOUSE"), rects[0]); name = demolish.name(g, rect)
    print("building", name, rect)
    game.command(f"tp aoe2mc {rect[0]-4} {pos0[v[0]][1]:.1f} {rect[2]-4}"); time.sleep(1)
    x, z = (rect[0] + rect[1]) / 2, (rect[2] + rect[3]) / 2
    y = pos0[v[0]][1]
    view = f"tp aoe2mc {x+9:.1f} {y+4:.1f} {z+9:.1f} facing {x:.1f} {y:.1f} {z:.1f}"
    game.command(view); time.sleep(4); client.shot(f"{D}/4a-building-before.png")
    game.command(f"tp aoe2mc {rect[0]-4} {pos0[v[0]][1]:.1f} {rect[2]-4}"); time.sleep(1)
    print("pick b", client.pick(g, rect))
    print("clicks b", g.clicks()); time.sleep(2)
    print("direct b", demolish.open_menu(g, "aoe2mc", (rect[0] + 1, rect[2] + 1))); time.sleep(2)
    client.shot(f"{D}/3-building-menu.png")
    client.click(*client.slot(demolish.ITEM[0], 6)); time.sleep(1); menu.clicks(g); time.sleep(4)
    print("ruins", getattr(g, "ruins", None))
    game.command(view)
    time.sleep(4); client.shot(f"{D}/4-building-after.png")
