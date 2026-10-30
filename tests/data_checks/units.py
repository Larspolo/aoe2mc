"""game/data/units.jsonl: the combat values of a unit (#1912)."""
import abilities

from . import NAMES, NUMBER, STATS, form, stats

KEYS = {                                        # the optional keys of units.jsonl: one per line (#4585);
                                                # the keys of the unit abilities: game/abilities (#4588)
    "accuracy": NUMBER,
    "convert": int,
    "ignore_armor": bool,
    "min_range": NUMBER,
    "miss": dict,
    "note": str,
    "sail": NUMBER,
    "sight": int,
    "volley": dict,
}


def check(row):
    form(row, {"name": str, **STATS}, KEYS | {m.KEY: m.TYPE for m in abilities.MODULES})
    stats(row)
    assert row.get("on_death", "MILITIA") in NAMES["units.jsonl"], row["name"]   # abilities.on_death (#4471)
    if "aura" in row:                                                     # abilities.aura (#4470)
        form(row["aura"], {"radius": NUMBER, "speed": NUMBER, "attack_speed": NUMBER, "units": list}, {})
        assert set(row["aura"]["units"]) <= NAMES["units.jsonl"], row["name"]
