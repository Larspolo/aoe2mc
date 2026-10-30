"""The speed charge of a unit (the Samurai, #4545)."""
from . import values

KEY, TYPE = "speed_charge", dict
UNITS = values(KEY)


def command(uuid, name, T=4):
    """The plugin command of the speed charge of unit name (the key "speed_charge" of data/units.jsonl), or None: the
    unit walks "speed" faster while its target is "min" to "max" tiles (× T blocks) away."""
    c = UNITS.get(name)
    return f"aoe speedcharge {uuid} {c['speed']} {c['min'] * T} {c['max'] * T}" if c else None
