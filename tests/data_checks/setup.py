"""game/data/setup.jsonl: a value of a setting of the game setup (#2264)."""
import os

from game import table

from . import NAMES, RES, form
from .setup_keys import TYPES

KEYS = {r["name"]: r for r in table.load("setup_keys.jsonl")}   # one line per key of setup.jsonl (#2558)


def check(row):
    assert set(row) - {"name"} <= set(KEYS), ("give the key its line in game/data/setup_keys.jsonl", row["name"])
    form(row, {"name": str}, {k: TYPES[r["type"]] for k, r in KEYS.items()})
    assert sum(k in row for k, r in KEYS.items() if r.get("kind")) == 1, row["name"]   # a resource level, a start age
    assert all(set(v) == {"food", "wood", "gold", "stone"} for v in row.get("sides", {}).values()), row["name"]   # #2441
    assert set(row.get("random", ())) <= {r["name"] for r in table.load("setup.jsonl") if "resources" in r}, row["name"]   # #2489
    assert set(row.get("units", ())) <= NAMES["units.jsonl"], row["name"]  # (#2265) or a game mode (#2347)
    assert row.get("treaty", "endless") == "endless", row["name"]   # Wonder Race: a treaty with no end (#2406)
    assert set(row.get("slow", ())) <= NAMES["train.jsonl"] | NAMES["build.jsonl"], row["name"]   # Turbo (#2359)
    assert row.get("loaded", "skip") in ("skip", "start") and ("help" in row or "module" not in row), row["name"]
    assert os.path.exists(os.path.join(os.path.dirname(table.__file__), row["module"] + ".py")) if "module" in row else True, row["name"]
    assert set(row.get("resources", RES)) == {"food", "wood", "gold", "stone"}, row["name"]
    assert all(isinstance(v, int) and v >= 0 for v in row.get("resources", {}).values()), row["name"]
    assert row.get("ages", 0) in range(5) and set(row.get("skip", ())) <= NAMES["train.jsonl"], row["name"]
    assert set(row.get("buildings", ())) <= NAMES["build.jsonl"] and set(row.get("villagers", ())) <= RES, row["name"]
    assert set(row.get("sites", ())) <= NAMES["buildings.jsonl"] and set(row.get("more", ())) <= NAMES["train.jsonl"], row["name"]
    assert all(set(v) == RES for v in row.get("start", {}).values()) and set(row.get("start", ())) <= NAMES["setup.jsonl"]
    assert set(row.get("swap", {}).items()) <= {(a, b) for a in NAMES["train.jsonl"] for b in NAMES["train.jsonl"]}
    assert set(row.get("side_buildings", ())) <= set(row.get("sides", ())), row["name"]   # #2462
    assert all(set(v) <= NAMES["build.jsonl"] for v in row.get("side_buildings", {}).values()), row["name"]
    assert {row["ring"][k] for k in ("wall", "gate")} <= NAMES["build.jsonl"] if "ring" in row else True, row["name"]
