"""game/data/editor_gaia.jsonl: a part of the AoE2 names of the objects that the editor palette shows in its tab Gaia
(#6036)."""
from . import form


def check(row):
    form(row, {"name": str})
    assert row["name"] == row["name"].upper() and row["name"].strip("_"), row["name"]
