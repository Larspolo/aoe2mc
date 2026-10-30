"""Unique technologies that give pass-through damage (#4335): the castle of the Mapuche researches Malon (Castle Age:
Bolas Riders, Slingers and Skirmishers) and the castle of the Italians researches Pirotechnia (Imperial Age: Hand
Cannoneers +15 %). The pass is the fields "passes" and "pass_part" of the values with technologies (combat.Stats),
so that "add" of an effect changes them, and `aoe range` sends them to the plugin."""
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def research(civ, tech):
    """A game of civ in the Imperial Age that researched tech at the castle."""
    server, g = setup(civ, food=3000, wood=3000, gold=3000, ages=3)
    assert train.queue(g, "Steve", CASTLE, tech)
    train.tick(g, train.seconds(g, tech, "CASTLE"))
    assert tech in g.techs
    return g


def added(tech, name, field):
    """The value of field that technology tech adds to unit name (from its line in data/train.jsonl)."""
    return getattr(train.TECHS[tech](name, combat.stats(name)), field) - getattr(combat.stats(name), field)


def test_only_their_own_castles_research_malon_and_pirotechnia():
    for civ, tech, other in (("MAPUCHE", "MALON", "PIROTECHNIA"), ("ITALIANS", "PIROTECHNIA", "MALON")):
        server, g = setup(civ, ages=3)
        train.open_menu(g, "Steve", CASTLE)
        assert f":{label(g, tech)}:" in menus(server)[-1]
        assert label(g, other) is None


def test_malon_gives_the_skirmisher_a_pass():
    server, g = setup("MAPUCHE", ages=3)
    assert combat.range_command("u", "SKIRMISHER", g.map.T, s=train.stats(g, "SKIRMISHER")).split()[5:] == []
    g = research("MAPUCHE", "MALON")
    tiles = added("MALON", "SKIRMISHER", "passes")
    assert tiles > 0
    words = combat.range_command("u", "SKIRMISHER", g.map.T, s=train.stats(g, "SKIRMISHER")).split()
    assert words[5:] == ["-", "0", f"{tiles * g.map.T}"]           # a mob shot ("-"), half damage: no part
    assert train.stats(g, "HAND_CANNONEER").passes == 0             # not a unit of Malon


def test_pirotechnia_adds_a_part_to_the_hand_cannoneer():
    g = research("ITALIANS", "PIROTECHNIA")
    before, after = combat.stats("HAND_CANNONEER"), train.stats(g, "HAND_CANNONEER")
    assert round(after.pass_part - before.pass_part, 6) == 0.15
    words = combat.range_command("u", "HAND_CANNONEER", g.map.T, s=after).split()
    assert words[5:] == ["-", "0", f"{after.passes * g.map.T}", str(after.pass_part)]
