"""The unique technologies of the Ethiopians and Dravidians with own damage rules (#4331): the castle of the Ethiopians
researches Royal Heirs (Castle Age: Shotel Warriors and camels take 3 less damage from mounted units), the castle of
the Dravidians Wootz Steel (Imperial Age: the hits of the infantry and cavalry ignore the armor), as in the AoE2 DE wiki
("Unique technology"). The rule is in combat.damage and in Stats.damage of the plugin: the mc test checks both."""
import shutil
import time

import pytest
from test_damage import health
from test_train_castle import menus, setup

from game import combat, run, train

CASTLE = (12, 4)
TECHS = {"ETHIOPIANS": "ROYAL_HEIRS", "DRAVIDIANS": "WOOTZ_STEEL"}


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


def test_royal_heirs_cuts_the_damage_of_a_knight_on_a_camel_rider():
    units, cut = train.value("less", "ROYAL_HEIRS")
    hits = train.hits(player("ETHIOPIANS", "ROYAL_HEIRS"), "CAMEL_RIDER")
    assert hits["less"] == cut and not hits["ignore"]
    base = combat.damage("KNIGHT", "CAMEL_RIDER")
    assert combat.damage("KNIGHT", "CAMEL_RIDER", **hits) == base - cut["cavalry"]
    assert combat.damage("CHAMPION", "CAMEL_RIDER", **hits) == combat.damage("CHAMPION", "CAMEL_RIDER")   # on foot
    assert train.hits(player("ETHIOPIANS"), "CAMEL_RIDER")["less"] == {}                     # no research
    assert train.hits(player("ETHIOPIANS", "ROYAL_HEIRS"), "KNIGHT")["less"] == {}           # not one of its units
    assert train.hits(player("ETHIOPIANS", "ROYAL_HEIRS"), "ELITE_SHOTEL_WARRIOR")["less"] == cut


def test_royal_heirs_counts_the_most_of_the_attacker_classes_and_keeps_one_damage():
    cut = {"cavalry": 3, "elephant": 3}
    t = combat.Stats(1000, 0, 0, 0, 0, 0.0, {}, ("infantry",))
    a = combat.Stats(100, 20, 0, 0, 0, 2.0, {}, ("cavalry", "elephant"))
    assert combat.damage("X", "Y", a, t, less=cut) == a.attack - 3                    # not 6 for two classes
    assert combat.damage("X", "Y", a._replace(attack=2), t, less=cut) == 1           # the AoE2 minimum


def test_wootz_steel_ignores_the_armor_of_the_target():
    g = player("DRAVIDIANS", "WOOTZ_STEEL")
    hits = train.hits(g, "CHAMPION")
    assert hits["ignore"] and hits["less"] == {}
    a, t = combat.stats("CHAMPION"), combat.stats("KNIGHT")
    assert t.melee > 0
    bonus = sum(a.bonus.get(c, 0) for c in t.classes)
    assert combat.damage("CHAMPION", "KNIGHT", **hits) == a.attack + bonus > combat.damage("CHAMPION", "KNIGHT")
    assert train.hits(g, "LIGHT_CAVALRY")["ignore"] and train.hits(g, "BATTLE_ELEPHANT")["ignore"]
    assert not train.hits(g, "ARBALESTER")["ignore"]                                  # an archer
    assert not train.hits(player("DRAVIDIANS"), "CHAMPION")["ignore"]                 # no research
    ram = combat.Stats(1000, 0, -3, 0, 0, 0.0, {}, ("siege",))                         # a negative armor still counts
    assert combat.damage("CHAMPION", "X", t=ram, ignore=True) == combat.damage("CHAMPION", "X", t=ram)


def fields(command):
    """The optional fields of an "aoe stats" command by name (key=value, #4460)."""
    return dict(w.split("=", 1) for w in command.split() if "=" in w)


def test_the_plugin_gets_the_damage_rules_with_the_stats():
    s = combat.stats("CAMEL_RIDER")
    assert combat.stats_command("u", "CAMEL_RIDER", s) == combat.stats_command("u", "CAMEL_RIDER")   # no new fields
    words = combat.stats_command("u", "CAMEL_RIDER", s, less={"cavalry": 3, "camel": 2}).split()
    assert fields(" ".join(words)) == {"less": "camel:2,cavalry:3"}                  # only the set fields
    assert fields(combat.stats_command("u", "CHAMPION", ignore=True)) == {"ignore": "1"}


def test_the_research_sends_the_new_rules_to_the_own_units():
    for civ, tech, name, word in (("ETHIOPIANS", "ROYAL_HEIRS", "CAMEL_RIDER", "cavalry:"),
                                  ("DRAVIDIANS", "WOOTZ_STEEL", "CHAMPION", None)):
        server, g = setup(civ, ages=3)
        g.soldiers["u1"] = name
        train.research(g, {"name": tech, "player": "Steve"})
        sent = [c for c in server.log if c.startswith("aoe stats u1 ")]
        assert sent and sent[-1] == combat.stats_command("u1", name, train.stats(g, name, "u1"), **train.hits(g, name))
        assert word in sent[-1] if word else fields(sent[-1]).get("ignore") == "1"


@pytest.mark.mc
def test_the_plugin_applies_the_damage_rules(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    less = {"camel": 3, "cavalry": 3, "elephant": 3}
    fights = (("KNIGHT", {}, "CAMEL_RIDER", {"less": less}), ("CHAMPION", {"ignore": True}, "KNIGHT", {}))
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 12} {z0 + 12}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 10} {y - 1} {z0 + 10} stone_bricks")
        game.command("time set midnight")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        for i, (attacker, a_rules, target, t_rules) in enumerate(fights):
            a, b, z = f"a{i}", f"b{i}", z0 + 2.5 + 6 * i
            for tag, dx, team, name, rules in ((a, 2, "p1", attacker, a_rules), (b, 4, "p2", target, t_rules)):
                game.command(f'summon zombie {x0 + dx + 0.5} {y} {z} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
                game.command(f"team join {team} @e[tag={tag}]")
                assert game.command(combat.stats_command(f"@e[tag={tag},limit=1]", name, **rules)).strip() == "Stats: 1 units"
            game.command(f"effect give @e[tag={b}] slowness infinite 255 true")
            full = combat.stats(target).hp
            one = combat.damage(attacker, target, **t_rules, **a_rules)              # per hit
            assert one != combat.damage(attacker, target)                            # the rule changes the hit
            assert health(game, b) == full
            assert game.command(f"aoe attack @e[tag={a}] @e[tag={b},limit=1]").strip() == "Attack: 1 units"
            end = time.time() + 30
            while time.time() < end and health(game, b) == full:
                time.sleep(0.1)
            time.sleep(0.2)
            assert health(game, b) in (full - one, full - 2 * one), (attacker, target, health(game, b))
