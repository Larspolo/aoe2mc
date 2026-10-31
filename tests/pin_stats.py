"""Test data for the combat values of a unit: a test that places units by a fixed distance pins the range of its
units, so that it passes with any valid unit data (tools/data_shake.py, #5399)."""
import sys

from game import combat


def pin(monkeypatch, name, **values):
    """Give unit name the combat values (for example range=5) in each copy of the module combat: game modules import it
    by its plain name too."""
    for mod in {id(m): m for m in (combat, sys.modules.get("combat")) if m}.values():
        monkeypatch.setitem(mod.STATS, name, mod.stats(name)._replace(**values))
