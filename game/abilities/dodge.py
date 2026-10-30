"""The dodge of a unit (the Shrivamsha Rider, #4399; the Iron Pagoda, #4465)."""
from . import values

KEY, TYPE = "dodge", dict
UNITS = values(KEY)


def command(uuid, name, T=4):
    """The plugin command of the dodge of unit name (the key "dodge" of data/units.jsonl), or None when it dodges
    nothing. The AoE2 wiki ("Shrivamsha Rider"): a second, regenerating health bar takes each projectile ("shots" of
    them in "time" AoE2 seconds) and fills again during combat; melee hits pass. The plugin fills the gauge evenly: one
    shot per time / shots seconds, up to shots. "melee": true (the Iron Pagoda, #4465): the gauge takes melee hits
    instead and projectiles pass; the command gets a last field 1."""
    d = UNITS.get(name)
    if not d:
        return None
    return f"aoe dodge {uuid} {d['shots']} {round(d['time'] * 20)}" + (" 1" if d.get("melee") else "")
