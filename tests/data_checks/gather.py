"""game/data/gather.jsonl: a resource, a drop site, a gather technology or an animal (#2033)."""
from . import NUMBER, RES, form


def check(row):
    form(row, {"name": str}, {"drop": list, "work": dict, "fish": int, "shore": bool, "hunt": int, "herd": bool,
                              "farm": int, "dark": bool, "ship": list, "civilian": bool, "mine": list, "carry": int,
                              "carry_rate": float,
                              "pace": float, "decay": float, "res": str})
    n = row["name"]
    assert len(row) > 1 and set(row.get("drop", ())) <= RES | {"meat"} and set(row.get("work", {})) <= RES, n
    assert all(isinstance(v, NUMBER) for v in row.get("work", {}).values()), n
    assert row.get("res", "food") in RES and ("res" not in row or "fish" in row), n   # an oyster: gold (#2465)
    assert type(row.get("watch", True)) in (bool, int), n         # true: Town Watch sight; a number: tiles (#3915)
    if "mine" in row:                                      # [the resource, its amount, the villager name of the miner]
        res, amount, miner = row["mine"]
        assert res in RES and isinstance(amount, int) and miner.isupper(), n
    assert len(row.get("ship", (0, 0))) == 2 and all(isinstance(v, NUMBER) for v in row.get("ship", ())), n
