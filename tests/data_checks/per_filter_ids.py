"""game/data/per_filter_ids.jsonl: a CmdId, ActionId or OrderId of up-filter-include and -exclude (#5131)."""
from . import form


def check(row):
    form(row, {"name": str, "id": int, "kind": str}, {"class": str, "units": list, "states": list})
    assert row["name"].startswith(f"{row['kind']}id-") and row["kind"] in ("cmd", "action", "order"), row["name"]
    assert row.get("class", "building") in ("building", "military", "monk", "resource", "villager"), row["name"]
    assert ("states" in row) <= (row["kind"] != "cmd") and ("class" in row or "units" in row) <= (row["kind"] == "cmd")
    assert all(isinstance(s, str) for s in row.get("states", []) + row.get("units", [])), row["name"]
