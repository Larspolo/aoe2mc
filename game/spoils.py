"""
Resources for kills and deaths in the game program (#2271, epic #1088), the civilization bonuses of AoE2 DE:
- Tupi (civs.FALLEN): a fallen own unit, except ships and siege weapons, gives 15 % of its cost back.
- Mapuche (civs.KILL_GOLD): each military unit that an own mounted unit kills gives 3 gold. Only the Paper plugin sees
  the killer: it counts these kills for each team in the score aoe_mounted_kills (AoePlugin.kill).
- Athenians, Military Policy (civs.policy, the effect key "kill_gold", #2512): each enemy unit that an own infantry or
  cavalry unit kills gives 5 gold, not a King or a trade unit. The plugin counts these kills for each team in the score
  aoe_unit_kills (AoePlugin.unitKill), also under another policy: only the kills while the policy is active pay.
- Varangian Guard and Keshik (combat.ATTACK_GOLD, #2376, #4464): 35 and 21.75 gold for each AoE2 minute that it
  attacks enemy units, the Varangians 50 % more (civs key "attack_gold"). Only the plugin sees a hit: each own unit with the tag aoe2mc.gold.N
  (N: gold per 100 minutes) adds N × its reload ticks to the score aoe_attack_gold of its team for each hit (AoePlugin.gold).
- Danes (civs.LOOT): an enemy building that falls after an attack order gives 25 % of its cost, not a wall or a gate.
AoE2 keeps the fractions of a part (g.spare, as the drop-off bonus): the next part gets them.

    spoils.fallen(g, dead)    # train.census: the own villagers and soldiers that died since the last count
    spoils.kills(g)           # train.census: the new kills of the plugin
    spoils.attacks(g)         # train.census: the new hits of the units with combat.ATTACK_GOLD
    spoils.loot(g, uuid)      # gather.Gather.fall: the target of the fallen building
"""
import re

import build
import civs
import combat
import fleet
import train

OBJECTIVE = "aoe_mounted_kills"   # the score of AoePlugin.java: kills of military units by mounted units, per team
UNIT_KILLS = "aoe_unit_kills"     # the score of AoePlugin.java: kills of enemy units by infantry and cavalry, per team
TRADE = "aoe2mc.trade"            # the tag of a trade unit: its kill gives no policy gold (AoePlugin.unitKill)
GOLD = "aoe_attack_gold"          # the score of AoePlugin.java: gold per 100 minutes × reload ticks of the hits, per team
PART = 100                        # the tag holds gold per 100 AoE2 minutes: 21.75 (Keshik) is a whole number (#4464)


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
        cost = "VILLAGER_MALE" if name == "VILLAGER" else name       # the census names each villager VILLAGER (#2966)
        if part and u not in seen and returns(name) and cost in train.COSTS:
            gain(g, train.price(g, cost), part)
        seen.add(u)


def kills(g):
    """Give civs.KILL_GOLD gold for each new kill of the team of g in the score of the plugin, and the "kill_gold" of
    the active policy for each new kill of an enemy unit (Athenians)."""
    if any("kill_gold" in e for e in civs.policies(g).get("effects", {}).values()):
        m = re.search(r"has (\d+)", g.command(f"scoreboard players get p{g.player} {UNIT_KILLS}") or "")
        n, seen = int(m.group(1)) if m else 0, vars(g).get("unit_kills", 0)
        if n > seen and (gold := civs.policy(g)[1].get("kill_gold")):
            g.earn("gold", gold * (n - seen))
        g.unit_kills = max(n, seen)                                    # the kills under another policy pay nothing
    gold = civs.KILL_GOLD.get(civs.civ(g))
    if not gold:
        return
    m = re.search(r"has (\d+)", g.command(f"scoreboard players get p{g.player} {OBJECTIVE}") or "")
    n = int(m.group(1)) if m else 0
    if n > vars(g).get("kills", 0):
        g.earn("gold", gold * (n - vars(g).get("kills", 0)))
    g.kills = max(n, vars(g).get("kills", 0))


def tag_command(uuid, name):
    """The command that lets the plugin count the hits of unit name (combat.ATTACK_GOLD), or that tags a trade unit
    (no policy gold for its kill, #2512), else None."""
    if civs.tagged(name, "trade units"):
        return f"tag {uuid} add {TRADE}"
    return f"tag {uuid} add aoe2mc.gold.{round(combat.ATTACK_GOLD[name] * PART)}" if name in combat.ATTACK_GOLD else None


def attacks(g):
    """Give the gold of the new hits of the own units with combat.ATTACK_GOLD in the score of the plugin: the score
    holds gold per 100 AoE2 minutes × real ticks at Normal speed, times the civ key "attack_gold" (Varangians 1.5).
    Remove the read value from the score: it stays far from the Java int limit, and new hits stay in it."""
    if not any(n in combat.ATTACK_GOLD for n in g.soldiers.values()):
        return
    m = re.search(r"has (\d+)", g.command(f"scoreboard players get p{g.player} {GOLD}") or "")
    if n := int(m.group(1)) if m else 0:
        g.command(f"scoreboard players remove p{g.player} {GOLD} {n}")
        gain(g, {"gold": n / PART / 20 * combat.NORMAL / 60}, civs.value("attack_gold", civs.civ(g), 1))


def loot(g, uuid):
    """Give the part civs.LOOT of the cost of the fallen enemy building with target uuid: not a wall or a gate."""
    name, part = g.fort_names.get(uuid, ""), civs.LOOT.get(civs.civ(g))
    if part and name not in combat.WALLS and "GATE" not in name:
        gain(g, build.COSTS.get(name, {}), part)
