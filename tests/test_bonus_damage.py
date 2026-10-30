"""game/civs.py: the bonus damage of the Bohemians, Gurjaras, Sicilians and Bengalis (AoE2 DE, #2248). The value "bonus"
multiplies the bonus damage that a unit deals, the value "taken" the bonus damage that it takes (the plugin gets it
with "aoe stats")."""
import shutil
import time

import pytest

from game import civs, combat, run, train

from test_civ_work import setup
from test_damage import health

AGES = {"DARK": (), "FEUDAL": ("FEUDAL_AGE",), "CASTLE": ("FEUDAL_AGE", "CASTLE_AGE"),
        "IMPERIAL": ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")}


def player(civ, age="DARK"):
    g = setup(civ)
    g.techs.update(AGES[age])
    return g


def hit(attacker, a_civ, target, t_civ, age="DARK"):
    """The damage of one hit of attacker (a player of a_civ) on target (a player of t_civ)."""
    a, t = player(a_civ, age), player(t_civ, age)
    return combat.damage(attacker, target, train.stats(a, attacker), train.stats(t, target), civs.taken(t, target))


def test_a_bohemian_pikeman_deals_more_bonus_damage():
    more, base = train.stats(player("BOHEMIANS"), "PIKEMAN").bonus["cavalry"], combat.stats("PIKEMAN").bonus["cavalry"]
    assert more > base
    assert hit("PIKEMAN", "BOHEMIANS", "KNIGHT", "FRANKS") - hit("PIKEMAN", "BRITONS", "KNIGHT", "FRANKS") == more - base
    assert train.stats(player("BOHEMIANS"), "MAN_AT_ARMS").bonus == combat.stats("MAN_AT_ARMS").bonus


def test_gurjara_mounted_units_deal_more_bonus_damage_in_each_age():
    base = combat.stats("CAMEL_RIDER").bonus["cavalry"]
    bonus = [train.stats(player("GURJARAS", age), "CAMEL_RIDER").bonus["cavalry"] for age in AGES]
    assert all(base <= a <= b for a, b in zip(bonus, bonus[1:])) and bonus[-1] > base
    castle = bonus[list(AGES).index("CASTLE")]
    assert hit("CAMEL_RIDER", "GURJARAS", "KNIGHT", "FRANKS", "CASTLE") - \
        hit("CAMEL_RIDER", "PERSIANS", "KNIGHT", "FRANKS", "CASTLE") == castle - base
    assert train.stats(player("GURJARAS", "CASTLE"), "PIKEMAN").bonus == combat.stats("PIKEMAN").bonus   # infantry: no bonus


def test_a_sicilian_knight_takes_less_bonus_damage():
    assert civs.taken(player("SICILIANS"), "KNIGHT") < 1
    assert hit("PIKEMAN", "BRITONS", "KNIGHT", "SICILIANS") < hit("PIKEMAN", "BRITONS", "KNIGHT", "FRANKS")


def test_a_sicilian_ram_villager_and_ship_take_the_full_bonus_damage():
    g = player("SICILIANS")
    assert [civs.taken(g, n) for n in ("BATTERING_RAM", "VILLAGER_MALE", "GALLEY")] == [1, 1, 1]
    assert hit("MANGONEL", "BRITONS", "BATTERING_RAM", "SICILIANS") == hit("MANGONEL", "BRITONS", "BATTERING_RAM", "FRANKS")


def test_a_bengali_elephant_takes_less_bonus_damage():
    taken = civs.taken(player("BENGALIS"), "BATTLE_ELEPHANT")
    assert taken < 1 and civs.taken(player("BENGALIS"), "KNIGHT") == 1
    bonus = combat.stats("PIKEMAN").bonus["elephant"]
    assert hit("PIKEMAN", "BRITONS", "BATTLE_ELEPHANT", "BENGALIS") \
        == hit("PIKEMAN", "BRITONS", "BATTLE_ELEPHANT", "BRITONS") - bonus + int(bonus * taken + 0.5)


def test_the_plugin_gets_the_factor_of_the_bonus_damage_taken():
    s = combat.stats("KNIGHT")
    assert combat.stats_command("u", "KNIGHT", s, 0.6).endswith(" taken=0.6")
    assert combat.stats_command("u", "KNIGHT", s) == combat.stats_command("u", "KNIGHT")   # 1: no last field
    assert "taken=" not in combat.stats_command("u", "KNIGHT")


@pytest.mark.mc
def test_the_plugin_takes_less_bonus_damage_from_a_hit(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 12} {z0 + 12}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 10} {y - 1} {z0 + 10} stone_bricks")
        game.command("time set midnight")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        for tag, dx, team, name, taken in (("a", 2, "p1", "PIKEMAN", 1.0), ("b", 4, "p2", "KNIGHT", 0.6)):
            game.command(f'summon zombie {x0 + dx + 0.5} {y} {z0 + 2.5} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join {team} @e[tag={tag}]")
            command = combat.stats_command(f"@e[tag={tag},limit=1]", name, None, taken)
            assert game.command(command).strip() == "Stats: 1 units"
        game.command("effect give @e[tag=b] slowness infinite 255 true")
        full = combat.stats("KNIGHT").hp
        one = combat.damage("PIKEMAN", "KNIGHT", combat.stats("PIKEMAN"), combat.stats("KNIGHT"), 0.6)   # per hit
        assert health(game, "b") == full
        assert game.command("aoe attack @e[tag=a] @e[tag=b,limit=1]").strip() == "Attack: 1 units"
        end = time.time() + 30
        while time.time() < end and health(game, "b") == full:
            time.sleep(0.1)
        time.sleep(0.2)
        assert health(game, "b") in (full - one, full - 2 * one), health(game, "b")
