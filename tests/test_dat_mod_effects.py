"""tools/dat_compare.py --write: the technology effects of a data mod .dat as data mod lines (#5668, epic #5352)."""
import json
from types import SimpleNamespace as NS

from tests.test_dat_compare import dat, unit
from tools import dat_compare as dc

EFFECT = {"if": [{"prefix": "VILLAGER"}], "add": {"melee": 1, "hp": 15}}


def tech_dat(cmds, time=30):
    d = dat([[], [unit(1, 40)]], {5: cmds})
    d.techs = [NS(resource_costs=[NS(type=0, amount=50, flag=1)], research_locations=[NS(research_time=time)],
                  effect_id=5, civ=0)]
    return d


def cmds(melee=1, kind=4):
    return [(kind, -1, 6, dc.ARMOR, 4 * 256 + melee), (4, -1, 6, dc.HP, 15)]


def lines(tmp_path, base, mod):
    t = {"train.jsonl": [{"name": "T", "effect": EFFECT, "cost": {"food": 50}, "time": 30}]}
    dc.write(base, mod, {}, t, str(tmp_path), techs={"T": 0}, civs={})
    return [json.loads(s) for s in open(tmp_path / "train.jsonl", encoding="utf-8")]


def test_a_changed_armor_amount_gives_one_line(tmp_path):
    assert lines(tmp_path, tech_dat(cmds()), tech_dat(cmds(3))) == [
        {"name": "T", "effect": {"if": EFFECT["if"], "add": {"melee": 3, "hp": 15}}}]


def test_the_same_dat_gives_no_line(tmp_path):
    assert lines(tmp_path, tech_dat(cmds()), tech_dat(cmds())) == []


def test_a_mul_command_gives_no_line_and_one_output_line(tmp_path, capsys):
    assert lines(tmp_path, tech_dat(cmds()), tech_dat(cmds(kind=5))) == []
    assert capsys.readouterr().out.count("T effect") == 1


def test_the_time_stays_in_the_line_of_the_effect(tmp_path):
    assert lines(tmp_path, tech_dat(cmds()), tech_dat(cmds(2), time=45)) == [
        {"name": "T", "time": 45, "effect": {"if": EFFECT["if"], "add": {"melee": 2, "hp": 15}}}]
