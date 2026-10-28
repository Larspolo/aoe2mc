"""
The regeneration of the units of some civilizations (#2247, part of #1088), as in AoE2 DE (the AoE2 wiki, "Civilization
bonuses"): Polish villagers 10/15/20, Georgian mounted units 2/8/14 and Wu infantry 10/15/30 hit points per AoE2 minute
in the Feudal/Castle/Imperial Age, Thracian elite skirmishers 5 and imperial skirmishers 10, Bengali ships 15, Puru
cavalry 25 from the Classical (Castle) Age with no enemy unit within 10 tiles (#2334) (civs.REGEN, the key "regen" of
data/civs.jsonl). A unit never gets more than its max_health. A ship has its hit points in its crew (repair.crew).

Minecraft feature: the same Health change as the monk heal (monk.py). The `regeneration` effect is not used: its rates
(1 health per 50, 25, 12 ... ticks) do not match the AoE2 rates, and the plugin cancels the natural heal of AoE2 units
(#850). One timer for all units: a pass every EVERY AoE2 seconds gives the hit points of all the time since the last one.

    regen.tick(g, dt)       # gather.Gather.step: dt AoE2 seconds of regeneration
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
