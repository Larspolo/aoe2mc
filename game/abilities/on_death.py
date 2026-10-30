"""The unit that rises where a unit dies (the Konnik, #4471)."""
from . import values

KEY, TYPE = "on_death", str
UNITS = values(KEY)
FELL = "aoe2mc.fell."            # the tag + UUID of the marker that the plugin leaves where a unit of UNITS dies


def command(uuid, name, T=4):
    """The command that tags unit name when another unit rises where it dies (the key "on_death" of data/units.jsonl),
    or None. The plugin leaves a marker with the tag FELL + uuid at the place of the death of a tagged unit
    (AoePlugin.onDeath); train.fell reads it. A removed unit (a sunk boat, an unloaded chunk) leaves none."""
    return f"tag {uuid} add aoe2mc.on_death" if name in UNITS else None
