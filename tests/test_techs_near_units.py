"""Values that depend on the own units near a unit (#4333, near.py): Shield Wall of the Saxons and Coiled Serpent Array
of the Shu (AoE2 DE wiki). The key "near" of a technology of data/train.jsonl: test lines here, not the values of the
data lines (#4242)."""
from test_train_castle import setup

import train as plain_train          # near.py imports train by its plain name (not game.train)
from game import civs, combat, near, train

ARMOR = {"if": [{"class": "infantry"}], "range": 3, "per": 2, "most": 2, "add": {"melee": 1, "pierce": 1}}
SIZE = {"if": [{"forms": ["SPEARMAN"]}], "range": 3, "per": 1, "most": 3, "part": {"hp": 0.1}}
AR, HP = "SHIELD_WALL", "COILED_SERPENT_ARRAY"


def game(monkeypatch, units):
    """A test game with the test lines AR (armor) and HP researched, and the own soldiers units {uuid: (name, x, z)}.
    The test lines take the names of two real technologies with the key "near" (train.stats needs a known name)."""
    for m in (train, plain_train):
        monkeypatch.setitem(m.BY_KEY, "near", {AR: ARMOR, HP: SIZE})
    server, g = setup("SAXONS", ages=3)
    g.techs |= {AR, HP}
    for u, (name, x, z) in units.items():
        g.soldiers[u] = name
        server.entities[u] = {"Pos": (x, 64.0, z)}
    return server, g


def pos(units):
    return {u: (x, 64.0, z) for u, (name, x, z) in units.items()}


GROUP = {f"m{k}": ("MILITIA", 1.0 + k * 0.5, 1.0) for k in range(5)} | {   # 5 militia within 2 blocks
    "far": ("MILITIA", 20.0, 20.0), "arch": ("ARCHER", 1.0, 1.5),
    "s0": ("SPEARMAN", 10.0, 1.0), "s1": ("PIKEMAN", 11.0, 1.0), "s2": ("HALBERDIER", 20.0, 1.0)}


def test_each_step_counts_the_other_units_of_the_tests_in_range(monkeypatch):
    server, g = game(monkeypatch, GROUP)
    out = near.steps(g, pos(GROUP))
    assert all(out[f"m{k}"][AR] == 2 for k in range(5))              # 4 others: 2 steps of 2, at most 2
    assert out["s0"] == out["s1"] == {HP: 1}                         # 1 other: no armor step of 2
    assert "far" not in out and "arch" not in out and "s2" not in out  # alone, not infantry, out of range
    g.techs -= {AR, HP}
    assert near.steps(g, pos(GROUP)) == {}                             # no research


def test_the_stats_of_a_unit_have_its_steps(monkeypatch):
    server, g = game(monkeypatch, GROUP)
    base = train.stats(g, "MILITIA")
    g.near = {"m0": {AR: 2}, "s0": {HP: 2}}
    s = train.stats(g, "MILITIA", "m0")
    assert (s.melee, s.pierce, s.hp) == (base.melee + 2, base.pierce + 2, base.hp)
    assert train.stats(g, "MILITIA", "far") == base
    assert train.stats(g, "SPEARMAN", "s0").hp == round(train.stats(g, "SPEARMAN").hp * 1.2)


def test_a_pass_sends_the_values_only_when_the_steps_change(monkeypatch):
    server, g = game(monkeypatch, GROUP)
    near.tick(g, near.EVERY / 2)
    assert not [c for c in server.log if c.startswith("aoe stats")]   # not yet a pass
    near.tick(g, near.EVERY / 2)
    sent = sorted(c.split()[2] for c in server.log if c.startswith("aoe stats"))
    assert sent == sorted([f"m{k}" for k in range(5)] + ["s0", "s1"])
    assert [c for c in server.log if c.startswith("aoe stats m0 ")] == [combat.stats_command(
        "m0", "MILITIA", train.stats(g, "MILITIA", "m0"), civs.taken(g, "MILITIA"), civs.friendly(g, "MILITIA"))]
    server.log.clear()
    near.tick(g, near.EVERY)
    assert not [c for c in server.log if c.startswith("aoe stats")]   # the same steps: no command
    server.entities["m4"]["Pos"] = (30.0, 64.0, 30.0)                  # one walks away: 3 others give 1 step
    near.tick(g, near.EVERY)
    assert sorted(c.split()[2] for c in server.log if c.startswith("aoe stats")) == [f"m{k}" for k in range(5)]
    assert g.near["m0"] == {AR: 1} and "m4" not in g.near
