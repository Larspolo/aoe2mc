"""The own charge attack of a unit (the Coustillier, #4398; the Urumi Swordsman, #4544)."""
from . import values

KEY, TYPE = "charge_attack", dict
UNITS = values(KEY)


def command(uuid, name, T=4):
    """The plugin command of the own charge attack of unit name (the key "charge_attack" of data/units.jsonl), or None:
    the first melee hit on a unit after a full charge of "time" AoE2 seconds has "attack" more (aoe chargeattack of
    #4370; its time as ticks at Normal speed). A "blast" {"part", "radius"} (the Urumi Swordsman, #4544): the charged
    hit also hurts the near enemy units, radius in tiles of T blocks."""
    from gather import NORMAL                    # gather imports train, train imports this package
    c = UNITS.get(name)
    if not c:
        return None
    b = f" {c['blast']['part']:g} {c['blast']['radius'] * T:g}" if c.get("blast") else ""
    return f"aoe chargeattack {uuid} {max(1, round(c['time'] / NORMAL * 20))} {c['attack']}{b}"
