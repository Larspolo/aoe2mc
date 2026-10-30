"""The low hit point form of a unit (the Jian Swordsman, #4472)."""
from . import values

KEY, TYPE = "low_hp", dict
UNITS = values(KEY)


def command(uuid, name, T=4):
    """The plugin command of the low hit point form of unit name (the key "low_hp" of data/units.jsonl), or None when
    it has none. The AoE2 wiki ("Jian Swordsman"): it switches by itself to its unshielded form below "hp" hit points
    (that melee and pierce armor, "speed" times the speed) and back at hp or more. The plugin checks the hit points
    each tick."""
    lo = UNITS.get(name)
    if not lo:
        return None
    return f"aoe lowhp {uuid} {lo['hp']:g} {lo['melee']} {lo['pierce']} {lo['speed']:g}"
