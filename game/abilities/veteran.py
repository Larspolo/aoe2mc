"""The kill bonus of a unit (the Jaguar Warrior, #4467)."""
from . import values

KEY, TYPE = "veteran", dict
UNITS = values(KEY)


def command(uuid, name, T=4):
    """The plugin command of the kill bonus of unit name (the key "veteran" of data/units.jsonl), or None. AoE2 wiki
    ("Jaguar Warrior"): "Gains +1 attack for each unit killed (up to 4)": "attack" for each kill, up to "max". The
    plugin keeps the kills of a unit when it gets the command again (an Elite upgrade)."""
    v = UNITS.get(name)
    return f"aoe veteran {uuid} {v['attack']} {v['max']}" if v else None
