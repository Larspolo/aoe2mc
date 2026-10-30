"""The frenzy of a unit (the Temple Guard, #4468)."""
from . import values

KEY, TYPE = "frenzy", dict
UNITS = values(KEY)


def command(uuid, name, T=4):
    """The plugin command of the frenzy of unit name (the key "frenzy" of data/units.jsonl), or None. The AoE2 wiki
    ("Temple Guard"): each attack makes the reload "less" seconds shorter for "time" seconds, down to "min" seconds.
    The values as ticks (AoE2 seconds x 20, as dodge)."""
    f = UNITS.get(name)
    if not f:
        return None
    return f"aoe frenzy {uuid} {round(f['less'] * 20)} {round(f['time'] * 20)} {round(f['min'] * 20)}"
