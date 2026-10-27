"""
The AoE2 conquest rule in the game program (#1135, epic #1134): a player without units and buildings is defeated, and
the last player wins. gather.Gather.run calls tick() each EVERY seconds (not each tick: one command per player and
check). The bot of player 2 has an own Gather that steps without run(), so only the game of the human player checks.
A unit is an entity with the tag aoe2mc.p<n> of its player (units.make_entity, also trained units), not its horse,
camel or boat (units.MOUNT). A building is the target entity of combat.building in the team p<n>: walls, gates and
Gaia objects have no target (combat.BUILDINGS), so they do not keep a player alive (AoE2 wiki, "Conquest"). A
construction site of the player counts as a building, as a foundation in AoE2, also when it is complete: a built
building has no target entity yet, so nothing can destroy it.
Only a player that had units or buildings once can lose: a player of the scenario with nothing (most test maps), or with
its entities not loaded yet, is not in the game. A defeated rival loses its rest (cheats.destroy) and the chat says so.
The human player sees "Defeat" when it has nothing left, "Victory" when no rival is left; the game then ends (g.ended).
Allies (the `team` of aoe2mc.json, gather.allied, #1313) win together, as in AoE2: "Victory" when all players of the
other teams are defeated, also while an ally is still in the game. A defeated ally does not end the game.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from units import MOUNT  # noqa: E402

import cheats  # noqa: E402

EVERY = 3.0          # seconds between two checks


def alive(g, n):
    """Player n has a unit, a building or a construction site that counts in the AoE2 conquest."""
    return any(s["player"] == n for s in g.sites) or any(
        "passed" in g.command(f"execute if entity {sel}")
        for sel in (f"@e[tag=aoe2mc.p{n},tag=!{MOUNT}]", f"@e[tag=aoe2mc.building,team=p{n}]"))


def tick(g):
    """Check the players each EVERY seconds: defeat the ones without units and buildings, end the game."""
    if g.ended or g.clock() < vars(g).get("conquest_at", 0.0):
        return
    g.conquest_at = g.clock() + EVERY
    seen, lost = vars(g).setdefault("conquest_seen", set()), vars(g).setdefault("defeated", set())
    for n in sorted(int(p) for p in g.players if int(p) and int(p) not in lost):
        if alive(g, n):
            seen.add(n)
        elif n in seen:
            lost.add(n)
            if n == g.player:
                return cheats.end("Defeat", "red")(g, None)
            cheats.destroy(g, n)
            g.command("tellraw @a " + json.dumps({"text": f"Player {n} is defeated.", "color": "red"}))
    from gather import allied                                       # gather imports this module
    if any(not allied(g.players, g.player, n) for n in lost) and all(allied(g.players, g.player, n) for n in seen - lost):
        cheats.end("Victory", "gold")(g, None)                      # a rival lost, and only allies are left (#1313)
