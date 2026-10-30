"""The charged volley of a unit (the Xianbei Raider, #4546)."""
from . import values

KEY, TYPE = "charged_volley", dict
UNITS = values(KEY)


def command(uuid, name, T=4):
    """The plugin command of the charged volley of unit name (the key "charged_volley" of data/units.jsonl), or None: a
    shot at a unit that is not siege after a full charge of "time" AoE2 seconds also fires "shots" arrows of "attack"
    with "bonus" (aoe chargedvolley; its time as ticks at Normal speed)."""
    from gather import NORMAL                    # gather imports train, train imports this package
    c = UNITS.get(name)
    if not c:
        return None
    bonus = ",".join(f"{k}:{v}" for k, v in sorted(c.get("bonus", {}).items())) or "-"
    return f"aoe chargedvolley {uuid} {max(1, round(c['time'] / NORMAL * 20))} {c['shots']} {c['attack']} {bonus}"
