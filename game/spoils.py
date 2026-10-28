"""
Resources for kills and deaths in the game program (#2271, epic #1088), the civilization bonuses of AoE2 DE:
- Tupi (civs.FALLEN): a fallen own unit, except ships and siege weapons, gives 15 % of its cost back.
- Mapuche (civs.KILL_GOLD): each military unit that an own mounted unit kills gives 3 gold. Only the Paper plugin sees
  the killer: it counts these kills for each team in the score aoe_mounted_kills (AoePlugin.kill).
- Danes (civs.LOOT): an enemy building that falls after an attack order gives 25 % of its cost, not a wall or a gate.
AoE2 keeps the fractions of a part (g.spare, as the drop-off bonus): the next part gets them.

    spoils.fallen(g, dead)    # train.census: the own villagers and soldiers that died since the last count
    spoils.kills(g)           # train.census: the new kills of the plugin
    spoils.loot(g, uuid)      # gather.Gather.fall: the target of the fallen building
"""
import re

import build
import civs
import combat
import fleet
import train

OBJECTIVE = "aoe_mounted_kills"   # the score of AoePlugin.java: kills of military units by mounted units, per team


def gain(g, cost, part):
    """Earn part of cost ({resource: amount}); the fractions wait in g.spare."""
    for r, v in sorted(cost.items()):
        g.spare[r] = g.spare.get(r, 0) + v * part
        if whole := int(g.spare[r] + 1e-9):
            g.spare[r] -= whole
            g.earn(r, whole)


def returns(name):
    """A fallen unit gives back a part of its cost: not a ship or a siege weapon (AoE2 DE, Tupi)."""
    classes = combat.stats(name).classes
    return name not in fleet.SPEEDS and "ship" not in classes and "siege" not in classes


def fallen(g, dead):
    """Give the part civs.FALLEN of the cost of the dead units ({uuid: AoE2 name}) of g; each unit only once."""
    part, seen = civs.FALLEN.get(civs.civ(g)), vars(g).setdefault("fallen", set())
    for u, name in sorted(dead.items()):
        if part and u not in seen and returns(name):
            gain(g, train.price(g, name), part)
        seen.add(u)


def kills(g):
    """Give civs.KILL_GOLD gold for each new kill of the team of g in the score of the plugin."""
    gold = civs.KILL_GOLD.get(civs.civ(g))
    if not gold:
        return
    m = re.search(r"has (\d+)", g.command(f"scoreboard players get p{g.player} {OBJECTIVE}") or "")
    n = int(m.group(1)) if m else 0
    if n > vars(g).get("kills", 0):
        g.earn("gold", gold * (n - vars(g).get("kills", 0)))
    g.kills = max(n, vars(g).get("kills", 0))


def loot(g, uuid):
    """Give the part civs.LOOT of the cost of the fallen enemy building with target uuid: not a wall or a gate."""
    name, part = g.fort_names.get(uuid, ""), civs.LOOT.get(civs.civ(g))
    if part and name not in combat.WALLS and "GATE" not in name:
        gain(g, build.COSTS.get(name, {}), part)
