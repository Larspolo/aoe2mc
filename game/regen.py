"""
The regeneration of the units of some civilizations (#2247, part of #1088), as in AoE2 DE (the AoE2 wiki, "Civilization
bonuses"): Polish villagers 10/15/20, Georgian mounted units 2/8/14 and Wu infantry 10/15/30 hit points per AoE2 minute
in the Feudal/Castle/Imperial Age, Thracian elite skirmishers 5 and imperial skirmishers 10, Bengali ships 15, Puru
cavalry 25 from the Classical (Castle) Age with no enemy unit within 10 tiles (#2334) (civs.REGEN, the key "regen" of
data/civs.jsonl). A unit never gets more than its max_health. A ship has its hit points in its crew (repair.crew).
The heal aura (aura, #2432): the complete Settlements of a Muisca player heal the allied human units within 3 tiles by
5/10/15/15 hit points per AoE2 minute in the Dark/Feudal/Castle/Imperial Age (civs.HEAL_AURA, the key "heal_aura").
The Achaemenid Military Town Center (military, #2496): the own military units within 16 tiles of it heal 20 hit points
per AoE2 minute and walk 15 % faster (the "aura" of its line in game/data/train.jsonl, train.ONE_BUILDING).
The heroes (heroes, #2688): an own unit with the key "regen" of data/units.jsonl (combat.REGEN: Attila the Hun and
Alaric the Goth of Battle Royale, 30 hit points per AoE2 minute) regenerates in each civilization and age.
The unit aura (units, #4366): after a technology with the key "unit_aura" of data/train.jsonl (Bimaristan), each own unit
of its group "from" heals the allied units of its "group" within its "range" tiles by its "rate" per AoE2 minute; not
itself, and several auras do not add up (the largest rate).

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
    units(g, dt)
    military(g, dt)
    heroes(g, dt)
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


def heroes(g, dt):
    """Give the own units of combat.REGEN (the heroes) their hit points of dt AoE2 seconds back."""
    import combat                                                  # combat imports gather, gather imports this module
    if not (names := {u: n for u, n in vars(g).get("soldiers", {}).items() if n in combat.REGEN}):
        return
    g.hero_time = vars(g).get("hero_time", 0.0) + dt
    if g.hero_time < EVERY:
        return
    dt, g.hero_time = g.hero_time, 0.0
    for u, n in sorted(names.items()):
        if (h := monk.health(g, u)) and h[0] < h[1]:
            g.command(f"data modify entity {u} Health set value {round(min(h[1], h[0] + combat.REGEN[n] * dt / 60), 3)}f")


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


def units(g, dt):
    """Heal the allied units near the own units of a researched "unit_aura" technology (train.BY_KEY) for dt AoE2 seconds."""
    import combat, gather, train                                   # they import gather, gather imports this module
    if not (auras := [a for t, a in sorted(train.BY_KEY["unit_aura"].items()) if t in g.techs]):
        return
    g.unit_aura_time = vars(g).get("unit_aura_time", 0.0) + dt
    if g.unit_aura_time < EVERY:
        return
    dt, g.unit_aura_time = g.unit_aura_time, 0.0
    names = {}
    for h in fog.gathers(g):
        if gather.allied(g.players, g.player, h.player):
            names |= {o["uuid"]: o["name"] for o in h.units if o.get("uuid") in h.villagers} | h.soldiers
    src = {(u, i) for i, a in enumerate(auras) for u, n in g.soldiers.items() if civs.GROUPS[a["from"]](n, combat.stats(n))}
    pos = g.where(set(names) | {u for u, _ in src})
    for u, (x, _, z) in sorted((u, p) for u, p in pos.items() if u in names):
        rate = max((a["rate"] for i, a in enumerate(auras) if civs.GROUPS[a["group"]](names[u], combat.stats(names[u]))
                    and any(m != u and m in pos and math.dist((x, z), pos[m][::2]) <= a["range"] * g.map.T
                            for m, j in src if j == i)), default=0)
        if rate and (hp := monk.health(g, u)) and hp[0] < hp[1]:
            g.command(f"data modify entity {u} Health set value {round(min(hp[1], hp[0] + rate * dt / 60), 3)}f")


def military(g, dt):
    """The upgraded own buildings of g with a "heal" aura (Military Town Center, train.ONE_BUILDING, #2496): heal the own
    military units within its "range" for dt AoE2 seconds, and give them its "speed" (g.hurried, train.speed)."""
    import ai, gather, train                                       # they import gather, gather imports this module
    rects = [(r, a) for r, n in sorted(vars(g).get("upgraded", {}).items())
             if (a := train.ONE_BUILDING.get(n)) and "heal" in a and r in train.homes(g)]
    if not rects and not vars(g).get("hurried"):
        return
    g.military_time = vars(g).get("military_time", 0.0) + dt
    if g.military_time < EVERY:
        return
    dt, g.military_time = g.military_time, 0.0
    names = {u: n for u, n in g.soldiers.items() if gather.military(n)}
    near = {}
    for u, (x, _, z) in sorted(g.where(set(names)).items()):     # the distance rule of Gather.aura_rate
        if a := next((a for (x0, x1, z0, z1), a in rects
                      if max(x0 - x, x - x1, z0 - z, z - z1) <= a["range"] * g.map.T), None):
            near[u] = a
    for u, a in near.items():
        ship = u in g.ships
        if (h := repair.unit_hp(g, u) if ship else monk.health(g, u)) and h[0] < h[1]:
            new = round(min(h[1], h[0] + a["heal"] * dt / 60), 3)
            g.command((repair.crew(u) + "data modify entity @s" if ship else f"data modify entity {u}")
                      + f" Health set value {new}f")
    old, g.hurried = vars(g).get("hurried", {}), {u: a["speed"] for u, a in near.items()}
    for u in sorted(u for u in old.keys() | g.hurried.keys() if old.get(u) != g.hurried.get(u) and u in names
                    and u not in g.ships):                         # a ship: fleet.tick reads train.speed
        g.command(ai.speed_command(u, names[u], g.map.T, gather.NORMAL * train.speed(g, names[u], u)))
