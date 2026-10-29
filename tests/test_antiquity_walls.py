"""The Granary researches of the walls and towers in Antiquity Mode (#3914, docs/research/antiquity.md, end of 1.5):
the build menu locks a wall, gate or tower until its research ("needs"). The rule modules read their data at import,
so the checks run in one child process with AOE2MC_RULES=antiquity."""
import json

from test_antiquity_setting import child

CODE = r'''
import json, sys, types
sys.path[:0] = ["game", "tests"]
import build, train
g = types.SimpleNamespace(techs={"TOOL_AGE"})
out = {"wall": build.locked(g, "SMALL_WALL"), "gate": build.locked(g, "SMALL_GATE"), "tower": build.locked(g, "WATCH_TOWER")}
g.techs |= {"SMALL_WALL_TECH"}
out |= {"wall_after": build.locked(g, "SMALL_WALL"), "gate_after": build.locked(g, "SMALL_GATE")}
g.techs = {"TOOL_AGE", "BRONZE_AGE", "IRON_AGE", "GUARD_TOWER_TECH"}
out["ballista_menu"] = train.unlocked(g, "BALLISTA_TOWER_TECH")
g.techs |= {"BALLISTICS"}
out["ballista_menu_after"] = train.unlocked(g, "BALLISTA_TOWER_TECH")
out["ballista"] = build.locked(g, "BALLISTA_TOWER")
g.techs |= {"BALLISTA_TOWER_TECH"}
out["ballista_after"] = build.locked(g, "BALLISTA_TOWER")
out["granary"] = sorted(r["name"] for r in train.ROWS if r.get("building") == "GRANARY")
print(json.dumps(out))
'''


def test_a_wall_or_tower_needs_its_granary_research():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    assert (out["wall"], out["gate"], out["tower"]) == ("Needs Small Wall", "Needs Small Wall", "Needs Watch Tower")
    assert out["wall_after"] is None and out["gate_after"] is None
    assert "SMALL_WALL_TECH" in out["granary"]


def test_the_ballista_tower_research_needs_ballistics():
    out = json.loads(child(CODE).stdout.splitlines()[-1])
    assert out["ballista_menu"] is False and out["ballista_menu_after"] is True
    assert out["ballista"] == "Needs Ballista Tower" and out["ballista_after"] is None
