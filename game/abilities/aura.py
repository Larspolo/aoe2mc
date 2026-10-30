"""The aura of a unit (the Centurion, #4470)."""
import units

from . import values

KEY, TYPE = "aura", dict
UNITS = values(KEY)


def command(uuid, name, T=4):
    """The plugin command of the aura of unit name (the key "aura" of data/units.jsonl), or None. AoE2 wiki
    "Centurion": the own units of "units" within "radius" tiles move "speed" and attack "attack_speed" faster; two
    auras do not add up, allies get nothing. The plugin finds these units by their type tags (aoe2mc.t<ID>)."""
    a = UNITS.get(name)
    if not a:
        return None
    ids = units.type_ids()
    tags = ",".join(f"aoe2mc.t{ids[n]}" for n in a["units"] if ids.get(n) is not None)
    return f"aoe aura {uuid} {a['radius'] * T:g} {a['speed']:g} {a['attack_speed']:g} {tags}" if tags else None
