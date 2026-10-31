"""The wild animals attack at the AoE2 search radius of 12 tiles (#5304): the sight of the data gives the distance."""
import json
from pathlib import Path

import combat
from gather import predator

ROWS = [json.loads(line) for line in (Path(combat.__file__).parent / "data/units.jsonl").read_text().splitlines()
        if line.strip()]
DAT = [r for r in ROWS if "#5304" in r.get("note", "")]


def test_predator_attack_distance_is_its_sight():
    assert DAT
    for r in DAT:
        assert predator(r["name"]), r["name"]
        cmd = combat.sight_command("u", r["name"], 4)
        assert cmd == f"aoe sight u {r['sight'] * 4}", (r["name"], cmd)


def test_values_are_the_combat_stats():
    for r in DAT:
        s = combat.stats(r["name"])
        assert (s.hp, s.attack, s.reload) == (r["hp"], r["attack"], r["reload"])
