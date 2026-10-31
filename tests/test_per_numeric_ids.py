"""game/per.py: a plain airef id names a unit, building or technology as its name does (#5182)."""
from test_bot_gather import bot_map

from game import per

VILLAGER = 83                                  # test values: airef "Objects" (per_names.jsonl)
WHEELBARROW = 213                              # airef "Techs": ri-wheel-barrow


def script():
    server, me, b = bot_map()
    b.g.stock.update(food=1000, wood=1000, gold=1000, stone=1000)
    return per.Script(per.parse(""), b), b


def test_train_takes_the_id_of_a_unit():
    s, b = script()
    s.act(None, ("train", VILLAGER))
    by_id = [e["name"] for q in b.g.queues.values() for e in q]
    s2, b2 = script()
    s2.act(None, ("train", "villager"))
    assert by_id and by_id == [e["name"] for q in b2.g.queues.values() for e in q]


def test_can_research_by_id_is_its_name():
    s, b = script()
    assert s.check(("can-research", WHEELBARROW)) == s.check(("can-research", "ri-wheel-barrow"))


def test_an_unknown_id_warns_once(capsys):
    s, b = script()
    s.act(None, ("train", 9999))
    s.act(None, ("train", 9999))
    assert capsys.readouterr().err.count("9999") == 1
