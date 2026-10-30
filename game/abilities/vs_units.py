"""The anti-unit mode of a unit (the Lou Chuan, #4505). combat.damage takes its attack and bonus at a unit."""
from . import values

KEY, TYPE = "vs_units", dict
UNITS = values(KEY)


def command(uuid, name, T=4):
    """The plugin command of the anti-unit mode of unit name (the key "vs_units" of data/units.jsonl), or None: at a
    unit it shoots from that range (tiles × T blocks) with that pierce attack and bonus."""
    v = UNITS.get(name)
    if not v:
        return None
    bonus = ",".join(f"{c}:{n}" for c, n in sorted(v.get("bonus", {}).items())) or "-"
    return f"aoe vsunits {uuid} {v['attack']} {bonus} {v['range'] * T}"
