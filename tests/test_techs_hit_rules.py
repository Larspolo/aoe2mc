"""The unique technologies of the Danes and Khitans with own hit rules (#4332): the castle of the Danes researches
Hamask (Castle Age: infantry +1 attack for each 10 % of lost hit points), the castle of the Khitans Lamellar Armor
(Castle Age: infantry and skirmishers give 25 % of the damage of each hit with no projectile back to the attacker), as
in the AoE2 DE wiki ("Unique technology"). Both rules change at each hit: the plugin applies them, the mc test checks."""
import shutil
import time

import pytest
from test_damage import health
from test_train_castle import menus, setup

from game import combat, run, train

CASTLE = (12, 4)
TECHS = {"DANES": "HAMASK", "KHITANS": "LAMELLAR_ARMOR"}


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def player(civ, *techs):
    """setup() of civ in the Imperial Age with the technologies techs."""
    _, g = setup(civ, ages=3)
    g.techs.update(techs)
    return g


def test_each_technology_is_only_in_the_castle_menu_of_its_civilization():
    for civ, tech in TECHS.items():
        for other in TECHS:
            server, g = setup(other, ages=3)
            train.open_menu(g, "Steve", CASTLE)
            if other == civ:
                assert f":{label(g, tech)}:" in menus(server)[-1]
            else:
                assert label(g, tech) is None


def test_hamask_gives_the_attack_for_each_ten_percent_of_lost_hit_points():
    _, rage = train.value("rage", "HAMASK")
    g = player("DANES", "HAMASK")
    hits = train.hits(g, "CHAMPION")
    assert hits["rage"] == rage and not hits["reflect"]
    full = combat.damage("CHAMPION", "KNIGHT", **hits)
    assert full == combat.damage("CHAMPION", "KNIGHT")                               # no hit points lost
    assert combat.damage("CHAMPION", "KNIGHT", **hits, lost=0.5) == full + 5 * rage
    assert combat.damage("CHAMPION", "KNIGHT", **hits, lost=0.59) == full + 5 * rage  # each full 10 %
    assert train.hits(player("DANES"), "CHAMPION")["rage"] == 0                       # no research
    assert train.hits(g, "ARBALESTER")["rage"] == 0                                    # not infantry


def test_lamellar_armor_reflects_from_infantry_and_skirmishers_only():
    _, part = train.value("reflect", "LAMELLAR_ARMOR")
    g = player("KHITANS", "LAMELLAR_ARMOR")
    for name in ("SPEARMAN", "ELITE_SKIRMISHER"):
        assert train.hits(g, name)["reflect"] == part and not train.hits(g, name)["rage"]
    assert train.hits(g, "KNIGHT")["reflect"] == 0
    assert train.hits(player("KHITANS"), "SPEARMAN")["reflect"] == 0                  # no research
    assert combat.damage("MILITIA", "SPEARMAN", **train.hits(g, "SPEARMAN")) == combat.damage("MILITIA", "SPEARMAN")


def fields(command):
    """The optional fields of an "aoe stats" command by name (key=value, #4460)."""
    return dict(w.split("=", 1) for w in command.split() if "=" in w)


def test_the_plugin_gets_the_hit_rules_with_the_stats():
    assert combat.stats_command("u", "CHAMPION", rage=0, reflect=0) == combat.stats_command("u", "CHAMPION")   # no flag
    assert fields(combat.stats_command("u", "CHAMPION", rage=2)) == {"rage": "2"}         # no Wootz Steel
    assert fields(combat.stats_command("u", "SPEARMAN", reflect=0.25)) == {"reflect": "0.25"}
    assert fields(combat.stats_command("u", "CHAMPION", ignore=True, rage=1)) == {"ignore": "1", "rage": "1"}


def test_the_research_sends_the_new_rules_to_the_own_units():
    for civ, tech, name, key in (("DANES", "HAMASK", "CHAMPION", "rage"), ("KHITANS", "LAMELLAR_ARMOR", "SPEARMAN", "reflect")):
        server, g = setup(civ, ages=3)
        g.soldiers["u1"] = name
        train.research(g, {"name": tech, "player": "Steve"})
        sent = [c for c in server.log if c.startswith("aoe stats u1 ")]
        assert sent and sent[-1] == combat.stats_command("u1", name, train.stats(g, name, "u1"), **train.hits(g, name))
        assert fields(sent[-1])[key] == f"{train.hits(g, name)[key]:g}"


@pytest.mark.mc
def test_the_plugin_applies_the_hit_rules(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    rage, part = train.value("rage", "HAMASK")[1], train.value("reflect", "LAMELLAR_ARMOR")[1]
    # (attacker, its rules, its health part, target, its rules)
    fights = (("CHAMPION", {"rage": rage}, 1.0, "KNIGHT", {}), ("CHAMPION", {"rage": rage}, 0.5, "KNIGHT", {}),
              ("MILITIA", {}, 1.0, "SPEARMAN", {"reflect": part}))
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 12} {z0 + 22}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 10} {y - 1} {z0 + 20} stone_bricks")
        game.command("time set midnight")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        hurt = []
        for i, (attacker, a_rules, share, target, t_rules) in enumerate(fights):
            a, b, z = f"a{i}", f"b{i}", z0 + 2.5 + 6 * i
            for tag, dx, team, name, rules in ((a, 2, "p1", attacker, a_rules), (b, 4, "p2", target, t_rules)):
                game.command(f'summon zombie {x0 + dx + 0.5} {y} {z} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
                game.command(f"team join {team} @e[tag={tag}]")
                assert game.command(combat.stats_command(f"@e[tag={tag},limit=1]", name, **rules)).strip() == "Stats: 1 units"
            start = combat.stats(attacker).hp * share
            game.command(f"data modify entity @e[tag={a},limit=1] Health set value {start:g}f")
            game.command(f"effect give @e[tag={b}] slowness infinite 255 true")
            full = combat.stats(target).hp
            assert health(game, b) == full and health(game, a) == start
            assert game.command(f"aoe attack @e[tag={a}] @e[tag={b},limit=1]").strip() == "Attack: 1 units"
            end = time.time() + 30
            while time.time() < end and health(game, b) == full:
                time.sleep(0.1)
            time.sleep(0.2)
            hurt.append((full - health(game, b), start - health(game, a)))
        one = combat.damage("CHAMPION", "KNIGHT")
        assert hurt[0][0] in (one, 2 * one), hurt                                    # full health: no more attack
        assert hurt[1][0] in (one + 5 * rage, 2 * (one + 5 * rage)), hurt            # half health: 5 × 10 % lost
        one = combat.damage("MILITIA", "SPEARMAN")
        hits = hurt[2][0] / one
        assert hits in (1, 2) and hurt[2][1] == pytest.approx(hits * one * part, abs=1e-3), hurt   # the militia takes 25 %
        assert hurt[0][1] == hurt[1][1] == 0, hurt                                   # no reflect without the rule
