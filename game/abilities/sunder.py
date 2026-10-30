"""The armor cut of a unit (the Obuch, #4466)."""
from . import values

KEY, TYPE = "sunder", int
UNITS = values(KEY)


def command(uuid, name, T=4):
    """The plugin command of the armor cut of unit name (the key "sunder" of data/units.jsonl), or None. AoE2 wiki
    ("Obuch"): "Reduces armor and pierce armor of units by 1 (cannot be reduced below 0) each with every attack": each
    hit lowers the melee and the pierce armor of the target by "sunder", down to 0."""
    n = UNITS.get(name)
    return f"aoe sunder {uuid} {n}" if n else None
