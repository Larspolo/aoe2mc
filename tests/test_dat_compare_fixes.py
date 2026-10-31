"""tools/dat_compare.py: the false differences of the first run on the owner's Mac (#5297). Test objects only."""
from types import SimpleNamespace as NS

from tools import dat_compare as dc


def unit(uid, hp=40, name="U", cls=6, rng=0.0, reload=2.0, attacks=((4, 4),), armours=((4, 0), (3, 1)), train=(),
         costs=(), bird=None, building=None):
    t50 = NS(attacks=[NS(class_=c, amount=a) for c, a in attacks], armours=[NS(class_=c, amount=a) for c, a in armours],
             max_range=rng, reload_time=reload)
    return NS(id=uid, class_=cls, name=name, hit_points=hp, line_of_sight=4.0, speed=0.9, type_50=t50, bird=bird,
              building=building, creatable=NS(train_locations=[NS(unit_id=u, train_time=t) for u, t in train],
                                              resource_costs=[NS(type=r, amount=a, flag=f) for r, a, f in costs]))


def dat(civ_units, effects=None, techs=()):
    """civ_units: one list of units per civilization (index 0: Gaia); effects: {id: [(type, a, b, c, d)]}."""
    size = 1 + max([u.id for units in civ_units for u in units] + [0])
    civs = []
    for units in civ_units:
        lst = [None] * size
        for u in units:
            lst[u.id] = u
        civs.append(NS(units=lst))
    eff = [NS(effect_commands=[]) for _ in range(900)]
    for i, cmds in (effects or {}).items():
        eff[i] = NS(effect_commands=[NS(type=t, a=a, b=b, c=c, d=d) for t, a, b, c, d in cmds])
    return NS(civs=civs, effects=eff, techs=list(techs))


def tech(civ=-1, effect=-1, costs=(), time=None):
    return NS(civ=civ, effect_id=effect, resource_costs=[NS(type=r, amount=a, flag=1) for r, a in costs],
              research_locations=[NS(research_time=time)] if time is not None else [])


def run(d, row):
    return dc.compare(d, {"U": 1}, {}, {"units.jsonl": [row]})


def test_the_work_rate_of_the_villager():                                   # cause 1
    food = unit(dc.GATHERERS["food"], bird=NS(work_rate=0.31, tasks=[NS(action_type=5, work_value_1=1.0)]))
    d = dat([[], [food]])
    assert dc.compare(d, {}, {}, {"AOE2_WORK": {"food": 0.31}}) == []
    assert dc.compare(d, {}, {}, {"AOE2_WORK": {"food": 0.5}}) == ["AOE2_WORK food: 0.5, 0.31"]


def test_a_placed_building_with_another_name():                             # cause 2
    tc = unit(1, 2400, name="RTWC", train=((-1, 100),), costs=((1, 275, 1), (2, 100, 0)),
              building=NS(head_unit=5, stack_unit_id=-1))
    placed = unit(5, 2400, name="RTWC1X", train=((dc.VILLAGER, 150),), costs=((1, 275, 1), (2, 100, 1)),
                  building=NS(head_unit=-1, stack_unit_id=1))
    d = dat([[], [tc, placed]])
    row = {"name": "TOWN_CENTER", "cost": {"wood": 275, "stone": 100}, "time": 150}
    assert dc.compare(d, {"TOWN_CENTER": 1}, {}, {"build.jsonl": [row]}) == []
    assert dc.compare(d, {"TOWN_CENTER": 1}, {}, {"build.jsonl": [{**row, "time": 100}]}) == ["TOWN_CENTER time: 100, 150"]


def test_a_gate_has_the_values_of_its_segment():                            # cause 3
    gate = unit(2, 1650, name="GTAX2", armours=((4, 0), (3, 0)), train=((dc.VILLAGER, 70),), costs=((2, 30, 1),),
                building=NS(head_unit=-1, stack_unit_id=3))
    segment = unit(3, 1650, name="GTAA2", armours=((4, 6), (3, 6)), building=NS(head_unit=2, stack_unit_id=-1))
    d = dat([[], [gate, segment]])
    tables = {"buildings.jsonl": [{"name": "GATE", "hp": 1650, "melee": 6, "pierce": 6}],
              "build.jsonl": [{"name": "GATE", "cost": {"stone": 30}, "time": 70}]}
    assert dc.compare(d, {"GATE": 2}, {}, tables) == []


def test_a_technology_line_and_a_unit_line_of_the_same_name():             # cause 4
    keep = unit(1, 2250, name="KEEP", train=((dc.VILLAGER, 80),), costs=((2, 125, 1),))
    d = dat([[], [keep]], techs=[tech(costs=((0, 500), (1, 350)), time=75)])
    row = {"name": "KEEP", "item": "book", "cost": {"food": 500, "wood": 350}, "time": 75}
    assert dc.compare(d, {"KEEP": 1}, {"KEEP": 0}, {"train.jsonl": [row]}) == []
    ratha = {"name": "ELITE_RATHA", "item": "minecart", "cost": {"wood": 60, "gold": 60}, "time": 18}
    assert dc.compare(d, {}, {"ELITE_RATHA": 0}, {"train.jsonl": [ratha]}) == []      # a unit line with no unit ID


def test_a_range_of_half_a_tile():                                          # cause 5
    d = dat([[], [unit(1, rng=2.5)]])
    assert run(d, {"name": "U", "range": 2.5}) == []
    assert run(d, {"name": "U", "range": 3}) == ["U range: 3, 2.5"]


def test_the_tolerance_of_the_reload():                                     # cause 6
    d = dat([[], [unit(1, reload=2.15)]])
    assert run(d, {"name": "U", "reload": 2.16}) == []
    assert run(d, {"name": "U", "reload": 2.2}) == ["U reload: 2.2, 2.15"]


def test_no_attack_cycle():                                                 # cause 7
    assert run(dat([[], [unit(1, reload=1.6)]]), {"name": "U", "reload": 0.0}) == []
    assert run(dat([[], [unit(1, reload=0.0)]]), {"name": "U", "reload": 2.0}) == []


def test_a_unit_of_gaia_only():                                             # cause 8
    d = dat([[unit(1, 30)], [], []])
    assert run(d, {"name": "U", "hp": 30}) == []
    assert run(d, {"name": "U", "hp": 20}) == ["U hp: 20, 30"]


def test_the_name_of_the_cavalry_archer_class():                            # cause 9
    d = dat([[], [unit(1, attacks=((4, 4), (28, 2)))]])
    assert run(d, {"name": "U", "bonus": {"cavalry_archer": 2}}) == []


def test_negative_bonuses_are_not_compared():                               # cause 10
    d = dat([[], [unit(1, attacks=((4, 4), (25, -1), (21, 2)))]])
    assert run(d, {"name": "U", "bonus": {"standard": 2}}) == []
    assert run(d, {"name": "U", "bonus": {"standard": 2, "fireship": -3}}) == []
    assert run(d, {"name": "U", "bonus": {"standard": 3}}) == ["U bonus: {'standard': 3}, {'standard': 2}"]


def test_a_line_that_keeps_another_unit():                                  # cause 11
    uid = dc.SAME_AS["TREBUCHET"]
    d = dat([[], [unit(1, 99), unit(uid, 150)]])
    assert dc.compare(d, {"TREBUCHET": 1}, {}, {"units.jsonl": [{"name": "TREBUCHET", "hp": 150}]}) == []
    farm = unit(dc.GATHERERS["farm"], bird=NS(work_rate=0.53, tasks=[]))
    assert dc.compare(dat([[], [farm]]), {}, {}, {"AOE2_WORK": {"farm": 0.33}}) == []    # ACCEPTED


def test_the_technology_names_of_tech_names_jsonl():                        # cause 12
    units, techs = dc.names()
    row = next(r for r in dc.rows("data/tech_names.jsonl") if r["tech"] in techs)
    assert techs[row["name"]] == techs[row["tech"]]


def test_only_the_technologies_of_the_civilization_of_the_line():           # rule 7
    donjon = unit(1, 625, name="DONJON", train=((dc.VILLAGER, 125),), costs=((2, 175, 1),))
    effects = {800: [(5, -1, 6, 101, 0.667)], 801: [(4, 1, -1, 0, 10)]}       # -33 % time; +10 hit points
    d = dat([[], [donjon], [donjon], [donjon]], effects, techs=[tech(civ=2, effect=800), tech(civ=2, effect=801)])
    civs = {"FRANKS": 3, "SICILIANS": 2}
    row = {"name": "DONJON", "cost": {"stone": 175}, "time": 83, "civs": ["SICILIANS"]}
    assert dc.compare(d, {"DONJON": 1}, {}, {"build.jsonl": [row]}, civs) == []                    # 125 × 0.667
    assert dc.compare(d, {"DONJON": 1}, {}, {"build.jsonl": [{**row, "civs": ["FRANKS"]}]}, civs) == [
        "DONJON time: 83, 125"]
    stat = {"name": "DONJON", "hp": 635}                          # the stat lines have no civilization bonus
    assert dc.compare(d, {"DONJON": 1}, {}, {"buildings.jsonl": [stat]}, civs) == ["DONJON hp: 635, 625"]
