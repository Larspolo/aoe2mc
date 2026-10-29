"""A bot in Antiquity Mode builds the Return of Rome drop sites and the Barracks, then advances to the Tool Age (#3715,
docs/research/antiquity.md, section 4). The rule modules read their data at import, so the check runs in a child
process with AOE2MC_RULES=antiquity."""
import json

from test_antiquity_setting import child

CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from test_bot_gather import bot_map
import build, bot
server, me, b = bot_map()
b.g.stock.update({r: 5000 for r in b.g.stock})
sites = []
for _ in range(12):
    b.build()
    for s in b.g.sites:
        if not s.get("done"):
            s["done"] = True
            sites.append(s["name"])
b.villagers = len(b.g.villagers)
b.age_up()
queued = [e["name"] for q in b.g.queues.values() for e in q]
print(json.dumps({"order": list(bot.ORDER), "near": bot.NEAR, "sites": sites, "queued": queued}))
'''


def test_the_bot_builds_the_drop_sites_and_advances_to_the_tool_age():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    assert out["order"][:3] == ["GRANARY", "STORAGE_PIT", "BARRACKS"]
    assert out["near"] == {"GRANARY": "food", "STORAGE_PIT": "wood"}
    assert {"GRANARY", "STORAGE_PIT", "BARRACKS"} <= set(out["sites"])
    assert "TOOL_AGE" in out["queued"]
