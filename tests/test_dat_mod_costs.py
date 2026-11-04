"""tools/dat_compare.py --write: the costs and times of a data mod .dat as data mod lines (#5355, epic #5352)."""
import json
from types import SimpleNamespace as NS

from tests.test_dat_compare import dat, unit
from tools import dat_compare as dc

FOOD, GOLD = 0, 3


def priced_dat(unit_cost=((FOOD, 60, 1),), tech_time=30, building_cost=((1, 100, 1),)):
    trained = unit(1, 40, train=(12,), costs=unit_cost)
    house = unit(2, 550, train=(dc.VILLAGER,), costs=building_cost)
    d = dat([[], [trained, house]])
    d.techs = [NS(resource_costs=[NS(type=FOOD, amount=50, flag=1)], research_locations=[NS(research_time=tech_time)],
                  effect_id=-1, civ=0)]
    return d


TABLES = {"train.jsonl": [{"name": "U", "cost": {"food": 60}, "time": 21},
                          {"name": "T", "effect": "x", "cost": {"food": 50}, "time": 30}],
          "build.jsonl": [{"name": "H", "cost": {"wood": 100}, "time": 21}]}


def lines(tmp_path, base, mod):
    n = dc.write(base, mod, {"U": 1, "H": 2}, TABLES, str(tmp_path), techs={"T": 0}, civs={})
    out = {f: [json.loads(s) for s in open(tmp_path / f, encoding="utf-8")] for f in ("train.jsonl", "build.jsonl")}
    assert n == sum(map(len, out.values()))
    return out


def test_changed_costs_and_times_give_one_line_each(tmp_path):
    mod = priced_dat(unit_cost=((FOOD, 60, 1), (GOLD, 20, 1)), tech_time=45, building_cost=((1, 80, 1),))
    assert lines(tmp_path, priced_dat(), mod) == {
        "train.jsonl": [{"name": "U", "cost": {"food": 60, "gold": 20}}, {"name": "T", "time": 45}],
        "build.jsonl": [{"name": "H", "cost": {"wood": 80}}]}


def test_no_change_gives_no_line(tmp_path):
    (tmp_path / "train.jsonl").write_text('{"name": "U", "time": 1}\n', encoding="utf-8")
    assert lines(tmp_path, priced_dat(), priced_dat()) == {"train.jsonl": [], "build.jsonl": []}


def test_a_removed_resource_goes(tmp_path):
    base = priced_dat(unit_cost=((FOOD, 60, 1), (GOLD, 20, 1)))
    t = dict(TABLES, **{"train.jsonl": [{"name": "U", "cost": {"food": 60, "gold": 20}}]})
    dc.write(base, priced_dat(), {"U": 1, "H": 2}, t, str(tmp_path), techs={"T": 0})
    assert [json.loads(s) for s in open(tmp_path / "train.jsonl")] == [{"name": "U", "cost": {"food": 60}}]
