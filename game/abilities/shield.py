"""The projectile obstruction of a unit (the Hussite Wagon, #4507)."""
from . import values

KEY, TYPE = "shield", dict
UNITS = values(KEY)


def command(uuid, name, T=4):
    """The plugin command of the projectile obstruction of unit name (the key "shield" of data/units.jsonl), or None.
    AoE2 DE wiki "Hussite Wagon": an enemy projectile that passes through its box deals "part" of its damage to the
    unit behind it, and the wagon takes "takes" damage. Minecraft feature: a vanilla projectile hits the first entity on
    its line, so the plugin gives that hit to the target of the shooter."""
    s = UNITS.get(name)
    return f"aoe shield {uuid} {s['part']:g} {s['takes']}" if s else None
