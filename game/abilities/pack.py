"""The pack bonus of a unit (the Monaspa, #4469)."""
import units

from . import values

KEY, TYPE = "pack", dict
UNITS = values(KEY)


def command(uuid, name, T=4):
    """The plugin command of the pack bonus of unit name (the key "pack" of data/units.jsonl), or None. AoE2 wiki
    "Monaspa": +1 attack for every "per" own units of the types "with" within "radius" tiles, up to "max"; the unit
    itself does not count. The plugin finds them by their type tags (aoe2mc.t<ID>, on the rider)."""
    p = UNITS.get(name)
    if not p:
        return None
    ids = units.type_ids()
    tags = ",".join(f"aoe2mc.t{ids[n]}" for n in p["with"] if ids.get(n) is not None)
    return f"aoe pack {uuid} {p['per']} {p['radius'] * T:g} {p['max']} {tags}" if tags else None
