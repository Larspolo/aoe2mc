"""
The regeneration of the units of some civilizations (#2247, part of #1088), as in AoE2 DE (the AoE2 wiki, "Civilization
bonuses"): Polish villagers 10/15/20, Georgian mounted units 2/8/14 and Wu infantry 10/15/30 hit points per AoE2 minute
in the Feudal/Castle/Imperial Age, Thracian elite skirmishers 5 and imperial skirmishers 10, Bengali ships 15, Puru
cavalry 25 from the Classical (Castle) Age with no enemy unit within 10 tiles (#2334) (civs.REGEN, the key "regen" of
data/civs.jsonl). A unit never gets more than its max_health. A ship has its hit points in its crew (repair.crew).
The heal aura (aura, #2432): the complete Settlements of a Muisca player heal the allied human units within 3 tiles by
5/10/15/15 hit points per AoE2 minute in the Dark/Feudal/Castle/Imperial Age (civs.HEAL_AURA, the key "heal_aura").

Minecraft feature: the same Health change as the monk heal (monk.py). The `regeneration` effect is not used: its rates
(1 health per 50, 25, 12 ... ticks) do not match the AoE2 rates, and the plugin cancels the natural heal of AoE2 units
(#850). One timer for all units: a pass every EVERY AoE2 seconds gives the hit points of all the time since the last one.

    regen.tick(g, dt)       # gather.Gather.step: dt AoE2 seconds of regeneration and of the heal aura
"""
import math

import civs
import fog
import monk
import repair

EVERY = 5.0     # AoE2 seconds between two passes (fewer commands)


def tick(g, dt):
    """Give the own units of g that regenerate (civs.regen) their hit points of dt AoE2 seconds back."""
    import combat                                                  # combat imports gather, gather imports this module
    aura(g, dt)
    if civs.civ(g) not in civs.REGEN:
        return
    g.regen_time = vars(g).get("regen_time", 0.0) + dt
    if g.regen_time < EVERY:
        return
    dt, g.regen_time = g.regen_time, 0.0
    names = {o["uuid"]: o["name"] for o in g.units if o.get("uuid") in g.villagers} | g.soldiers
    foes = fog.units(g)[1] if any(len(r) > 2 for r in civs.REGEN[civs.civ(g)]) else {}   # only for a radius rule
    pos = g.where(set(names) | set(foes)) if foes else {}
    for u, n in sorted(names.items()):
        foe = min((math.dist(pos[u][::2], p[::2]) / g.map.T for f, p in pos.items() if f in foes and u in pos),
                  default=math.inf)
        if not (rate := civs.regen(g, n, combat.stats(n), foe)):
            continue
        ship = u in g.ships
        if (h := repair.unit_hp(g, u) if ship else monk.health(g, u)) and h[0] < h[1]:
            new = round(min(h[1], h[0] + rate * dt / 60), 3)
            g.command((repair.crew(u) + "data modify entity @s" if ship else f"data modify entity {u}")
                      + f" Health set value {new}f")


def aura(g, dt):
    """Heal the allied units of the group of civs.HEAL_AURA near the complete own buildings of g for dt AoE2 seconds."""
    import build, combat, gather, train                            # they import gather, gather imports this module
    if not (heals := civs.HEAL_AURA.get(civs.civ(g))):
        return
    g.aura_time = vars(g).get("aura_time", 0.0) + dt
    if g.aura_time < EVERY:
        return
    dt, g.aura_time = g.aura_time, 0.0
    rects = [(r, heals[n]) for r, n in sorted(train.homes(g).items()) if n in heals]
    if not rects:
        return
    names = {}
    for h in fog.gathers(g):
        if gather.allied(g.players, g.player, h.player):
            names |= {o["uuid"]: o["name"] for o in h.units if o.get("uuid") in h.villagers} | h.soldiers
    age = min(build.ages(g), 3)
    for u, (x, _, z) in sorted(g.where(set(names)).items()):
        rate = max((a["rate"][age] for (x0, x1, z0, z1), a in rects if civs.GROUPS[a["group"]](names[u], combat.stats(names[u]))
                    and x0 - (r := a["range"] * g.map.T) <= x < x1 + r and z0 - r <= z < z1 + r), default=0)
        if rate and (hp := monk.health(g, u)) and hp[0] < hp[1]:
            g.command(f"data modify entity {u} Health set value {round(min(hp[1], hp[0] + rate * dt / 60), 3)}f")
