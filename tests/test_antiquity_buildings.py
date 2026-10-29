"""The Return of Rome buildings in the build menu of Antiquity Mode (#3668, docs/research/antiquity.md, 1.3): cost, age,
footprint, the building that must stand first ("unlocked_by"), and the drop sites Granary and Storage Pit. The rule
modules read their data at import, so the checks run in one child process with AOE2MC_RULES=antiquity."""
import json

from test_antiquity_setting import child

from buildings import footprint
from game import build, table

ROR = ["ACADEMY", "ARCHERY_RANGE", "BALLISTA_TOWER", "BARRACKS", "DOCK", "FARM", "FORTIFIED_GATE", "FORTIFIED_WALL",
       "GOVERNMENT_CENTER", "GRANARY", "GUARD_TOWER", "HOUSE", "MARKET", "MEDIUM_GATE", "MEDIUM_WALL", "SENTRY_TOWER",
       "SIEGE_WORKSHOP", "SMALL_GATE", "SMALL_WALL", "STABLE", "STORAGE_PIT", "TEMPLE", "TOWN_CENTER", "WATCH_TOWER",
       "WONDER"]
CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from test_build_done import done
import build, gather
out = {"menu": build.MENU, "drops": {}, "stock": {}}
for name, res in [("GRANARY", "food"), ("STORAGE_PIT", "wood")]:
    server, g, cells = done(name)
    out["drops"][name] = sorted(r for r, sites in g.map.drops.items() if cells in sites)
    v = g.villagers["v0"]
    before = g.stock[res]
    v.state, v.load, v.res, v.tree = "to_drop", 7, res, None
    g.go(v, "to_drop", set().union(*map(g.map.around, g.map.drops[res])))
    for _ in range(len(v.path) + 2):
        g.step()
    out["stock"][name] = g.stock[res] - before
    if name == "GRANARY":                                              # a complete granary unlocks the market
        g.techs = {"TOOL_AGE"}
        out["market"] = build.locked(g, "MARKET")
        g.sites.clear()
        out["no_granary"] = build.locked(g, "MARKET")
print(json.dumps(out))
'''


def test_the_build_menu_has_the_return_of_rome_buildings_and_drop_sites():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    assert sorted(out["menu"]) == ROR
    assert out["drops"] == {"GRANARY": ["food"], "STORAGE_PIT": ["gold", "meat", "stone", "wood"]}
    assert out["stock"] == {"GRANARY": 7, "STORAGE_PIT": 7}
    assert out["market"] is None and out["no_granary"] == "Needs a Granary"


def test_each_building_has_cost_age_and_footprint():
    rows = {r["name"]: r for r in table.load("build.jsonl", rules="antiquity")}
    assert all("cost" in rows[n] and "time" in rows[n] for n in ROR)
    assert {n: rows[n].get("age", 0) for n in ROR if rows[n].get("age", 0) == 0} == dict.fromkeys(
        ["BARRACKS", "DOCK", "GRANARY", "HOUSE", "STORAGE_PIT", "TOWN_CENTER"], 0)          # the Stone Age
    assert {footprint(n) for n in ["ACADEMY", "GOVERNMENT_CENTER", "GRANARY", "STORAGE_PIT", "TEMPLE"]} == {3}
    assert footprint("STORAGE") == 2 and footprint("TEMPLE_OF_HEAVEN") == 5 and footprint("TEMPLE_RUIN") == 2
    assert all(rows[n]["unlocked_by"] in rows for n in rows if "unlocked_by" in rows[n])


def test_without_antiquity_the_build_menu_stays():
    assert "GRANARY" not in build.MENU and "MILL" in build.MENU and not build.UNLOCKED_BY
