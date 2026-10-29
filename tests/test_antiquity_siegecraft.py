"""Siegecraft of Antiquity Mode (#3916, Return of Rome): after it the villagers attack the enemy walls and towers
(gather.breach), and a villager next to the wall hits it once per reload with a `damage` command by the villager (the
plugin gives the AoE2 damage). The rule modules read their data at import, so the checks run in one child process."""
import json

from test_antiquity_setting import child

CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from test_forging import setup
import combat, gather
out = {}
server, g = setup(age=0)
wall, tower, house = (combat.target_uuid([x, 9, x + 1, 10]) for x in (9, 12, 15))
for u, name, x in ((wall, "STONE_WALL", 9), (tower, "WATCH_TOWER", 12), (house, "HOUSE", 15)):
    g.forts[u], g.fort_names[u] = (x, 64, 9, x, 67, 9), name
out["before"] = [gather.breach(g, u) for u in (wall, tower, house)]
g.techs.add("SIEGECRAFT")
out["after"] = [gather.breach(g, u) for u in (wall, tower, house)]
v = g.villagers["v"]
g.hunt(wall, {"v"})
out["state"], out["prey"] = v.state, v.prey
v.state, v.pos, v.path = "hunt", (8.5, 64.0, 9.5), []
del server.log[:]
for _ in range(int(gather.VILLAGER_HIT[1] / gather.NORMAL / g.tick) + 2):
    g.strike(v)
out["hits"] = [c for c in server.log if c.startswith("damage ")]
g.forts.pop(wall)                                                  # the wall falls (Gather.fall)
g.strike(v)
out["end"] = v.state, v.prey
print(json.dumps(out))
'''


def test_villagers_attack_walls_and_towers_after_siegecraft():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    assert out["before"] == [False, False, False]                    # no attack on a wall before Siegecraft
    assert out["after"] == [True, True, False]                       # walls and towers, not a house
    assert out["state"] == "to_prey" and out["prey"]
    assert out["hits"] and all(h.endswith(" minecraft:mob_attack by v") for h in out["hits"])
    assert out["end"] == ["idle", None]
