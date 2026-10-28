"""
The start scout of a civilization in the game program (#2391, epic #1088; AoE2 wiki "Scout unit"): on most maps a
player starts with a Scout Cavalry, the Aztecs and Mayans with an Eagle Scout, the Gurjaras with a Camel Scout, and the
Incas, Mapuche, Muisca and Tupi with a Champi Scout. The scout of a civilization is the key "scout" of its line in
game/data/civs.jsonl. The civilization of a player can change before the game (run.py --civ, #2267), so run.play swaps
each Scout Cavalry of the map for the scout of the civilization at the start of a new game. A loaded game has its
scouts in the world already, and a map with no scout gets no new one.
"""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cheats  # noqa: E402
import civs  # noqa: E402
import table  # noqa: E402

SCOUTS = {r["name"]: r["scout"] for r in table.load("civs.jsonl") if "scout" in r}
CAVALRY = "SCOUT_CAVALRY"                                              # the start scout of the other civilizations


def used(data):
    """True when a player of aoe2mc.json data has a civilization with its own scout."""
    return any(SCOUTS.get(p.get("civ")) for p in dict(data.get("players") or {}).values())


def swap(g):
    """Turn each own Scout Cavalry of g into the scout of its civilization at the same place (cheats.transform)."""
    if name := SCOUTS.get(civs.civ(g)):
        cheats.transform(g, types.SimpleNamespace(units=lambda n: n == CAVALRY, to=name))
