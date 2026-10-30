"""The blast technologies of five civilizations (#4328): Druzhina (Slavs), Greek Fire and Logistica (Byzantines),
Vendel Legacy (Varangians), Lechitic Legacy (Poles) and Cilician Fleet (Armenians). Each shows only in the castle
menu of its civilization, gives the units of its lines the blast radius of its data line, and the range parts add
range."""
import pytest
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)
TECHS = {"DRUZHINA": "SLAVS", "GREEK_FIRE": "BYZANTINES", "LOGISTICA": "BYZANTINES", "VENDEL_LEGACY": "VARANGIANS",
         "LECHITIC_LEGACY": "POLES", "CILICIAN_FLEET": "ARMENIANS"}
UNITS = {"DRUZHINA": "MILITIA", "GREEK_FIRE": "DROMON", "LOGISTICA": "CATAPHRACT", "VENDEL_LEGACY": "PALADIN",
         "LECHITIC_LEGACY": "HUSSAR", "CILICIAN_FLEET": "HEAVY_DEMOLITION_SHIP"}


def label(g, name):
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def research(civ, tech):
    server, g = setup(civ, food=3000, wood=3000, gold=3000, ages=3)
    assert train.queue(g, "Steve", CASTLE, tech)
    train.tick(g, train.seconds(g, tech, "CASTLE"))
    assert tech in g.techs
    return g


@pytest.mark.parametrize("tech", TECHS)
def test_only_the_castle_of_its_civilization_researches_it(tech):
    server, g = setup(TECHS[tech], ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, tech)}:" in menus(server)[-1]
    other = next(c for c in ("BRITONS", "FRANKS") if c != TECHS[tech])
    assert label(setup(other, ages=3)[1], tech) is None


@pytest.mark.parametrize("tech", TECHS)
def test_the_research_adds_the_blast_of_the_data_line(tech):
    unit = UNITS[tech]
    added = train.TECHS[tech](unit, combat.stats(unit)).blast - combat.stats(unit).blast
    assert added > 0
    _, g = setup(TECHS[tech], ages=3)
    assert train.stats(g, unit).blast == combat.stats(unit).blast               # no research: no change
    g = research(TECHS[tech], tech)
    assert train.stats(g, unit).blast == pytest.approx(combat.stats(unit).blast + added)
    assert train.stats(g, "ARCHER") == combat.stats("ARCHER")                   # not a unit of its lines


@pytest.mark.parametrize("tech, unit", [("GREEK_FIRE", "FIRE_SHIP"), ("CILICIAN_FLEET", "GALLEON"),
                                        ("CILICIAN_FLEET", "DROMON")])
def test_the_range_parts_add_one_range(tech, unit):
    _, g = setup(TECHS[tech], ages=3)
    before = train.stats(g, unit).range
    assert train.stats(research(TECHS[tech], tech), unit).range == before + 1
