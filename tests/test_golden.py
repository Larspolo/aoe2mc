"""Golden test: shows each change of the output of the tiny scenario.

If a change of the output is on purpose, write a new golden file and explain the change in the PR:
    AOE2MC_UPDATE_GOLDEN=1 python3 -m pytest tests/test_golden.py
"""
import json
import os
from collections import Counter

import world_reader

GOLDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden", "tiny.json")


def digest(path):
    """For each chunk the sorted counts of block states, and the list of entities (ID, position, name tag)."""
    w = world_reader.World(path)
    chunks = {}
    for (cx, cz), c in sorted(w.chunks().items()):
        n = Counter()
        for s in c["sections"]:
            names, idx = w.section_states(s)
            n.update(names[i] for i in idx)
        chunks[f"{cx},{cz}"] = dict(sorted(n.items()))
    entities = sorted([str(e["id"]), [round(float(v), 1) for v in e["Pos"]],
                       json.loads(str(e["CustomName"]))["text"] if "CustomName" in e else None]
                      for e in w.entities())
    return {"chunks": chunks, "entities": entities}


def test_golden(tiny_world):
    d = digest(tiny_world[0])
    if os.environ.get("AOE2MC_UPDATE_GOLDEN"):
        with open(GOLDEN, "w") as f:
            json.dump(d, f, indent=1, sort_keys=True)
            f.write("\n")
    with open(GOLDEN) as f:
        golden = json.load(f)
    for k in sorted(set(golden["chunks"]) | set(d["chunks"])):
        assert d["chunks"].get(k) == golden["chunks"].get(k), f"chunk {k} changed"
    assert d["entities"] == golden["entities"]
