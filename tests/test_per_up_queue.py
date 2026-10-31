"""game/per.py: up-train, up-build and up-research take a name (c:) or a goal that holds an airef id (g:) (#4869)."""
import pytest
from test_bot_gather import bot_map

from game import per
from game.bot import train  # the module that per uses

IDS = {"villager": 83, "house": 70, "ri-loom": 22}                     # test values: airef "Objects" and "Techs"


def script(text=""):
    server, me, b = bot_map()
    b.g.stock.update(food=1000, wood=1000, gold=1000, stone=1000)
    s = per.Script(per.parse(text), b)
    s.goals.update({1: 0, 2: IDS["villager"], 3: IDS["house"], 4: IDS["ri-loom"]})
    return s, b


def ref(type_op, name, goal):
    return ("c:", name) if type_op == "c:" else ("g:", goal)


@pytest.fixture(autouse=True)
def ids(monkeypatch):
    monkeypatch.setattr(per, "OBJECT_IDS", {IDS["villager"]: "villager", IDS["house"]: "house"})
    monkeypatch.setattr(per, "TECH_IDS", {IDS["ri-loom"]: "ri-loom"})


@pytest.mark.parametrize("type_op", ["c:", "g:"])
def test_the_can_facts_and_the_counts(type_op):
    s, b = script()
    assert s.check(("up-can-train", 1, *ref(type_op, "villager", 2)))
    assert s.check(("up-can-build", 1, *ref(type_op, "house", 3)))
    assert s.check(("up-can-research", 1, *ref(type_op, "ri-loom", 4)))
    alive = s.count("VILLAGER_MALE")
    assert s.check(("up-object-type-count", *ref(type_op, "villager", 2), "==", alive))
    assert s.check(("up-object-type-count-total", *ref(type_op, "villager", 2), "==", alive))


@pytest.mark.parametrize("type_op", ["c:", "g:"])
def test_the_queue_commands(type_op):
    s, b = script()
    total = s.count("VILLAGER_MALE", total=True)
    s.act(None, ("up-train", 1, *ref(type_op, "villager", 2)))
    assert s.check(("up-object-type-count-total", *ref(type_op, "villager", 2), "==", total + 1))
    s.act(None, ("up-research", 1, *ref(type_op, "ri-loom", 4)))
    assert train.queued(b.g, "LOOM")
    s.act(None, ("up-build", "place-normal", 1, *ref(type_op, "house", 3)))
    assert any(x["name"] == "HOUSE" for x in b.g.sites)
    assert s.count("HOUSE", total=True) > s.count("HOUSE")


def test_an_unknown_id_does_nothing(capsys):
    s, b = script()
    s.goals[2] = 9999
    s.act(None, ("up-train", 1, "g:", 2))
    assert not any(b.g.queues.values()) and "unknown id 9999" in capsys.readouterr().err


@pytest.mark.parametrize("escrow", [0, 1])
def test_up_train_spends_the_escrow_only_with_escrow(escrow):
    s, b = script()
    food = train.price(b.g, "VILLAGER_MALE")["food"]
    s.escrow["food"] = b.g.stock["food"] = 2 * food
    s.goals[1] = escrow
    s.act(None, ("up-train", 1, "c:", "villager"))
    assert bool(any(b.g.queues.values())) == bool(escrow)              # escrow 0: the free stock is 0
    assert s.escrow["food"] == (food if escrow else 2 * food)


def test_up_build_warns_of_another_placement(capsys):
    s, b = script()
    s.act(None, ("up-build", "place-sideways", 1, "c:", "house"))
    assert "unknown placement place-sideways" in capsys.readouterr().err
    assert any(x["name"] == "HOUSE" for x in b.g.sites)
