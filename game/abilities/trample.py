"""The trample damage of a unit (the elephants, #4397). train.trample_command gives the splash of a technology
(Druzhina, #4496), stance.mode_commands the trample of a mode (the Ratha, #4504): both with t."""
from . import values

KEY, TYPE = "trample", dict
UNITS = values(KEY)


def command(uuid, name, T=4, t=None):
    """The plugin command of the trample damage of unit name (the key "trample" of data/units.jsonl), or None. Each
    melee hit also hurts the other enemy units within "radius" tiles (× T blocks) of the target with "part" of the AoE2
    damage on each (AoE2 DE wiki "Trample damage"). t: other values, for example of a technology (epic #4096): a fixed
    "damage" instead of the part, and "ignore": true for a damage that ignores the armor."""
    t = t or UNITS.get(name)
    if not t:
        return None
    fixed = f" {t['damage']:g} {int(bool(t.get('ignore')))}" if t.get("damage") else ""
    return f"aoe trample {uuid} {t.get('part', 0):g} {round(t['radius'] * T, 6):g}{fixed}"
