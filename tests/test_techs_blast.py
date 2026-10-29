"""Unique technologies that change the blast radius (#4283): the castle of the Britons researches Warwolf (Trebuchets
+0.5 blast radius) and the castle of the Ethiopians researches Torsion Engines (rams +0.5, the Mangonel line and
Bombard Cannons +0.45) in the Imperial Age, with the values of the AoE2 DE wiki ("Unique technology"). The radius is
the field "blast" of the values with technologies (combat.Stats), so that "add" of an effect changes it."""
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def blast(g, name):
    """The blast radius in blocks of the `aoe range` command of unit name of the player of g."""
    return float(combat.range_command("u", name, g.map.T, s=train.stats(g, name)).split()[5])


def added(tech, name):
    """The blast radius in tiles that technology tech adds to unit name (from its line in data/train.jsonl)."""
    return train.TECHS[tech](name, combat.stats(name)).blast - combat.stats(name).blast


def test_only_their_own_castles_research_warwolf_and_torsion_engines():
    for civ, tech, other in (("BRITONS", "WARWOLF", "TORSION_ENGINES"), ("ETHIOPIANS", "TORSION_ENGINES", "WARWOLF")):
        server, g = setup(civ, ages=3)
        train.open_menu(g, "Steve", CASTLE)
        assert f":{label(g, tech)}:" in menus(server)[-1]
        assert label(g, other) is None


def test_warwolf_gives_the_trebuchet_a_blast_radius():
    server, g = setup("BRITONS", food=3000, wood=3000, gold=3000, ages=3)
    assert blast(g, "TREBUCHET") == 0                              # one target only, as in AoE2 before Warwolf
    onager = train.stats(g, "ONAGER")
    assert train.queue(g, "Steve", CASTLE, "WARWOLF")
    train.tick(g, train.seconds(g, "WARWOLF", "CASTLE"))
    assert "WARWOLF" in g.techs
    assert added("WARWOLF", "TREBUCHET") > 0
    assert blast(g, "TREBUCHET") == added("WARWOLF", "TREBUCHET") * g.map.T
    assert train.stats(g, "ONAGER") == onager                      # not a trebuchet


def test_torsion_engines_add_blast_to_rams_mangonels_and_bombard_cannons():
    server, g = setup("ETHIOPIANS", food=3000, wood=3000, gold=3000, ages=3)
    names = ("SIEGE_ONAGER", "MANGONEL", "BOMBARD_CANNON", "CAPPED_RAM")
    before = {n: blast(g, n) for n in names}
    trebuchet = train.stats(g, "TREBUCHET")
    assert train.queue(g, "Steve", CASTLE, "TORSION_ENGINES")
    train.tick(g, train.seconds(g, "TORSION_ENGINES", "CASTLE"))
    assert "TORSION_ENGINES" in g.techs
    for n in names:
        assert added("TORSION_ENGINES", n) > 0
        assert blast(g, n) == round((combat.BLAST.get(n, 0) + added("TORSION_ENGINES", n)) * g.map.T, 6) > before[n]
    assert train.stats(g, "TREBUCHET") == trebuchet                # not a ram, mangonel or bombard cannon


def test_a_research_sends_the_new_blast_to_the_live_units():
    server, g = setup("ETHIOPIANS", food=3000, wood=3000, gold=3000, ages=3)
    g.soldiers["live-onager"] = "ONAGER"
    server.entities["live-onager"] = {"Pos": (6.5, 64.0, 12.5)}      # a live unit has a position (train.census)
    server.log.clear()
    assert train.queue(g, "Steve", CASTLE, "TORSION_ENGINES")
    train.tick(g, train.seconds(g, "TORSION_ENGINES", "CASTLE"))
    sent = [c for c in server.log if c.startswith("aoe range live-onager ")]
    assert sent and float(sent[-1].split()[5]) == blast(g, "ONAGER")


def test_a_player_with_no_research_keeps_the_blast_of_the_data():
    server, g = setup("ETHIOPIANS", ages=3)
    for n in ("ONAGER", "BOMBARD_CANNON", "TREBUCHET"):
        assert blast(g, n) == round(combat.BLAST.get(n, 0) * g.map.T, 6)
