"""The charged shot that slows its target (the Bolas Rider, #4548)."""
from . import values

KEY, TYPE = "snare", dict
UNITS = values(KEY)


def command(uuid, name, T=4):
    """The plugin command of the charged shot of unit name (the key "snare" of data/units.jsonl), or None: the first
    projectile hit after a charge of "time" AoE2 seconds has "attack" more and slows the target by "slow" for "for"
    seconds. Minecraft slowness lowers the speed by 15 % for each level: amplifier = slow / 0.15 - 1. The ticks as in
    charge.command."""
    from gather import NORMAL  # gather imports train, train imports this package
    c = UNITS.get(name)
    if not c:
        return None
    ticks = [max(1, round(c[k] / NORMAL * 20)) for k in ("time", "for")]
    return f"aoe snare {uuid} {ticks[0]} {c['attack']} {round(c['slow'] / 0.15) - 1} {ticks[1]}"
