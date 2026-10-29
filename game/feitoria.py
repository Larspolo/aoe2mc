"""The Feitoria of the Portuguese (#4082): each complete own Feitoria adds food, wood, gold and stone to the stock of
its player, with no villagers (AoE2 DE wiki "Feitoria": 96 food, 42 wood, 60 gold and 18 stone per minute;
the key "trickle" of game/data/buildings.jsonl).

    feitoria.tick(g, dt)    # gather.Gather.step: dt AoE2 seconds of income
"""
import ruins
import table

RATE = {r["name"]: r["trickle"] for r in table.load("buildings.jsonl") if "trickle" in r}   # per AoE2 second


def count(g, name):
    """The complete own buildings of a name: the start ones that did not fall and the built ones (a fallen site leaves
    g.sites)."""
    return sum(o["kind"] == "building" and o["name"] == name and o["player"] == g.player and not ruins.fallen(g, o)
               for o in g.data["objects"]) + sum(s["name"] == name and bool(s.get("done")) for s in g.sites)


def tick(g, dt):
    """Add dt AoE2 seconds of income; keep the parts below 1 for the next tick."""
    part = vars(g).setdefault("feitoria_part", {})
    for name, rates in RATE.items():
        if n := count(g, name):
            for res, rate in rates.items():
                part[res] = part.get(res, 0.0) + rate * dt * n
    for res in part:
        if (whole := int(part[res] + 1e-9)) > 0:                      # 40 × 0.175 is 6.99999…
            part[res] -= whole
            g.earn(res, whole)
