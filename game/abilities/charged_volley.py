"""The charged volley of a unit (the Xianbei Raider, #4546; the Fire Lancer, #4547)."""
from . import values

KEY, TYPE = "charged_volley", dict
UNITS = values(KEY)


def command(uuid, name, T=4):
    """The plugin command of the charged volley of unit name (the key "charged_volley" of data/units.jsonl), or None: a
    shot at a unit that is not siege after a full charge of "time" AoE2 seconds also fires "shots" arrows of "attack"
    with "bonus" (aoe chargedvolley; its time as ticks at Normal speed). The optional "range" (tiles × T blocks: a melee
    unit fires at its target in it, the Fire Lancer, #4547) and "ignore" (the shots ignore the armor) are extra fields."""
    from gather import NORMAL  # gather imports train, train imports this package
    c = UNITS.get(name)
    if not c:
        return None
    bonus = ",".join(f"{k}:{v}" for k, v in sorted(c.get("bonus", {}).items())) or "-"
    extra = f" {c.get('range', 0) * T} {int(c.get('ignore', False))}" if "range" in c or c.get("ignore") else ""
    return f"aoe chargedvolley {uuid} {max(1, round(c['time'] / NORMAL * 20))} {c['shots']} {c['attack']} {bonus}" + extra
