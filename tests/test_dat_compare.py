"""tools/dat_compare.py with test objects: no .dat, no genieutils-py (#5245)."""
from types import SimpleNamespace as NS

from tools import dat_compare as dc


def unit(uid, hp, attack=4, cls=6, name="U", train=(), costs=()):
    t50 = NS(attacks=[NS(class_=4, amount=attack)], armours=[NS(class_=4, amount=0), NS(class_=3, amount=1),
                                                             NS(class_=31, amount=0)], max_range=0.0, reload_time=2.0)
    return NS(id=uid, class_=cls, name=name, hit_points=hp, line_of_sight=4.0, speed=0.9, type_50=t50, bird=None,
              creatable=NS(train_locations=[NS(unit_id=u, train_time=21) for u in train],
                           resource_costs=[NS(type=r, amount=a, flag=f) for r, a, f in costs]))


def dat(civ_units, effects=None):
    """civ_units: one list of units per civilization (index 0: Gaia)."""
    civs = []
    for units in civ_units:
        lst = [None] * 10
        for u in units:
            lst[u.id] = u
        civs.append(NS(units=lst))
    eff = [NS(effect_commands=[]) for _ in range(900)]
    for i, cmds in (effects or {}).items():
        eff[i] = NS(effect_commands=[NS(type=t, a=a, b=b, c=c, d=d) for t, a, b, c, d in cmds])
    return NS(civs=civs, effects=eff, techs=[])


def run(d, row, units=None):
    return dc.compare(d, units or {"U": 1}, {}, {"units.jsonl": [row]})


def test_most_common_value_of_the_civilizations():
    d = dat([[unit(1, 99)], [unit(1, 40)], [unit(1, 40)], [unit(1, 55)]])      # rule 1: Gaia and one civ differ
    assert run(d, {"name": "U", "hp": 40}) == []
    assert run(d, {"name": "U", "hp": 55}) == ["U hp: 55, 40"]


def test_an_age_effect_makes_a_value_correct():
    d = dat([[], [unit(1, 40)], [unit(1, 40)]], {102: [(4, 1, -1, 0, 10)]})     # rule 2, 3: Castle Age +10 HP
    assert run(d, {"name": "U", "hp": 50}) == []
    assert run(d, {"name": "U", "hp": 51}) == ["U hp: 51, 40"]


def test_class_effect_on_the_attack():
    d = dat([[], [unit(1, 40)]], {101: [(4, -1, 6, 9, 4 * 256 + 2)]})       # rule 3: class 6, attack class 4 +2
    assert run(d, {"name": "U", "attack": 6}) == []
    assert run(d, {"name": "U", "attack": 7}) == ["U attack: 7, 4"]
    assert run(d, {"name": "U", "melee": 0, "pierce": 1, "bonus": {}}) == []   # class 31 ignored


def test_a_placed_building_has_the_unit_of_the_villager():
    tc = unit(1, 2400, name="TC", train=(), costs=((1, 275, 1), (2, 100, 0)))
    placed = unit(5, 2400, name="TC", train=(dc.VILLAGER,), costs=((1, 275, 1), (2, 100, 1)))
    d = dat([[], [tc, placed]])
    row = {"name": "TOWN_CENTER", "cost": {"wood": 275, "stone": 100}, "time": 21}
    assert dc.compare(d, {"TOWN_CENTER": 1}, {}, {"build.jsonl": [row]}) == []          # rule 5
    assert dc.compare(d, {"TOWN_CENTER": 1}, {}, {"build.jsonl": [{**row, "time": 30}]}) == ["TOWN_CENTER time: 30, 21"]


def test_no_dat_exits_2(tmp_path, capsys):
    assert dc.main([str(tmp_path / "none.dat")]) == 2
    assert "no .dat" in capsys.readouterr().out
