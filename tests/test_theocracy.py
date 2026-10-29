"""Theocracy (#1586): the monastery researches it in the Imperial Age (AoE2 wiki "Theocracy (Age of
Empires II)"). Before it, all monks that convert one unit rest after the conversion; after it, only the one that
converts it."""
from test_gather import FakeServer, grid
from test_monk_techs import MONASTERY, research
from test_monk_train import monastery

from game import gather, monk, train


def test_the_monastery_researches_it_only_in_the_imperial_age():
    slot, gold = train.ITEMS["THEOCRACY"][0], train.COSTS["THEOCRACY"]["gold"]
    server, g = monastery(age=2)
    g.stock["gold"] = gold
    rect = train.open_menu(g, "Steve", MONASTERY)
    assert train.order(g, "Steve", rect, slot) == 0 and g.stock["gold"] == gold
    server, g = monastery(age=3)
    rect = research(g, slot, gold)
    assert g.queues[rect][0]["name"] == "THEOCRACY"
    train.tick(g, train.TRAIN_TIMES["THEOCRACY"])
    assert "THEOCRACY" in g.techs


def group(*techs):
    """Three own monks next to each other and two enemy militia 7 tiles away: all three monks convert the first one."""
    objects = [{"kind": "unit", "name": "MONK", "player": 1, "uuid": f"m{i}", "tile": [5.5, 5.5 + i]} for i in range(3)]
    objects += [{"kind": "unit", "name": "MILITIA", "player": 2, "uuid": f"foe{i}", "tile": [12.5, 5.5 + i]}
                for i in range(2)]
    ents = {o["uuid"]: {"Pos": (o["tile"][0], 64.0, o["tile"][1])} for o in objects}
    g = gather.Gather(FakeServer(ents), grid([[64] * 40 for _ in range(40)], objects)).setup()
    g.techs |= set(techs)
    assert monk.convert_order(g, {"m0", "m1", "m2"}, "foe0")
    t = 0.0
    while "foe0" in g.enemies and t < 20:
        monk.convert(g, 0.25)
        t += 0.25
    assert "foe0" in g.soldiers and not g.converting
    return g


def test_without_it_all_monks_of_the_group_rest():
    g = group()
    assert set(g.faith) == {"m0", "m1", "m2"} and all(f > monk.REST - 1 for f in g.faith.values())
    assert monk.convert_order(g, {"m1"}, "foe1")
    monk.convert(g, 0.25)
    assert g.converting["m1"][1] == 0, "it rests: no chant"


def test_with_it_only_one_monk_rests_and_the_others_convert_at_once():
    g = group("THEOCRACY")
    assert len(g.faith) == 1 and list(g.faith.values())[0] > monk.REST - 1
    free = sorted({"m0", "m1", "m2"} - set(g.faith))[0]
    assert monk.convert_order(g, {free}, "foe1")
    monk.convert(g, 0.25)
    assert g.converting[free][1] > 0, "it chants at once"
