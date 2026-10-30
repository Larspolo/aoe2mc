"""The special abilities of the units (epic #4387): one module per ability. The package finds its modules by itself (no
list, #4588), so a new ability adds one file and changes no shared line of combat.py or train.py.

Each module has KEY (its key of data/units.jsonl), TYPE (the type of its value: tests/data_checks/units.py), UNITS
({unit name: value}, values(KEY)) and command(uuid, name, T): the plugin command of the ability of unit name (T blocks
per tile), or None. combat.setup, train.summon and train.research (an elite upgrade) send commands()."""
import importlib
import pkgutil

import table

ROWS = table.load("units.jsonl")             # the rule set of the game (table.RULES), as combat.UNIT_ROWS


def values(key):
    """{unit name: value} of the lines of data/units.jsonl with the key."""
    return {r["name"]: r[key] for r in ROWS if key in r}


MODULES = [importlib.import_module(f"{__name__}.{m.name}") for m in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name)]


def commands(uuid, name, T):
    """The plugin commands of all abilities of unit name, in the order of the module names."""
    return [c for m in MODULES if (c := m.command(uuid, name, T))]
