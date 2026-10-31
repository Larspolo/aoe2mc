"""game/per.py: the airef ids of the unit lines (militiaman-line -296) and -1 as all units (#5233)."""
from test_per_rules import run

from game import per, table
from game.bot import train  # the module that per uses

ROWS = {r["name"]: r for r in table.load("per_names.jsonl")}


def upgrade_id(techs=()):
    line = ROWS["militiaman-line"]["id"]
    s, b, _ = run(f"""(defrule (true) => (set-goal 100 {line}) (up-get-upgrade-id my-player-number 1 100 101)
(up-store-type-name g: 101) (disable-self))""")
    return s, b


def test_a_line_in_a_goal_gives_the_id_of_its_current_unit():
    s, b = upgrade_id()
    unit = s.upgraded(b.g, ROWS["militiaman-line"]["game"])
    assert s.goals[101] == per.TYPE_IDS[unit]
    assert s.text == per.OBJECT_IDS[per.TYPE_IDS[unit]]
    assert not s.warned


def test_the_line_name_is_a_goal_number():
    s, b, _ = run("(defrule (true) => (set-goal 100 militiaman-line) (disable-self))")
    assert s.goals[100] == ROWS["militiaman-line"]["id"] and not s.warned


def test_the_upgrade_id_follows_the_upgrade():
    s, b = upgrade_id()
    t = next(t for t in train.UPGRADES if any(old == "MILITIA" for old, _ in train.lines(t, b.g)))
    b.g.techs.add(t) if isinstance(b.g.techs, set) else b.g.techs.append(t)
    s.act(None, ("up-get-upgrade-id", "my-player-number", 1, 100, 102))
    assert s.goals[102] == per.TYPE_IDS[s.upgraded(b.g, "MILITIA")] != per.TYPE_IDS["MILITIA"]


def test_up_reset_unit_minus_one_stops_all_soldiers():
    s, b, _ = run("(defrule (false) => (do-nothing))")
    for i, m in enumerate(("MILITIA", "ARCHER")):
        b.g.soldiers[f"u{i}"] = m
    sent = []
    b.g.command = lambda c: sent.append(c)
    s.act(None, ("up-reset-unit", "c:", -1))
    assert {"aoe stop u0", "aoe stop u1"} <= set(sent) and not s.warned
