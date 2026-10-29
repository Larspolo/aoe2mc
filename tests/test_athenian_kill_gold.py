"""#2512: with the Athenian Military Policy each enemy unit that an own infantry or cavalry unit kills gives gold (AoE2
wiki "Military Policy"), not a King or a trade unit. The plugin counts the kills in the score aoe_unit_kills.
Fake server of test_gather."""
import re
import shutil
import time

import pytest
from test_kill_spoils import game
from test_mounted_attack import floor
from test_ranged import data

from game import civs, combat, run, spoils, train


def scores(server, **n):
    """The plugin answers n[objective] for the scores of player 1."""
    command = server.command
    server.command = lambda c: (f"p1 has {n[c.split()[-1]]} [{c.split()[-1]}]"
                                if c.startswith("scoreboard players get p1 ") and c.split()[-1] in n else command(c))
    return n


def test_the_military_policy_gives_gold_for_each_new_kill():
    server, g = game("ATHENIANS")
    g.policy = "MILITARY_POLICY"
    gold = civs.policy(g)[1]["kill_gold"]
    n = scores(server, **{spoils.UNIT_KILLS: 1})
    train.census(g)
    assert g.stock["gold"] == gold
    train.census(g)
    assert g.stock["gold"] == gold                                     # no new kill
    n[spoils.UNIT_KILLS] = 3
    train.census(g)
    assert g.stock["gold"] == 3 * gold


def test_the_kills_under_the_economic_policy_give_no_gold_also_after_a_switch():
    server, g = game("ATHENIANS")
    assert g.__dict__.get("policy") is None                            # the start policy: Economic
    n = scores(server, **{spoils.UNIT_KILLS: 2})
    train.census(g)
    assert g.stock["gold"] == 0
    g.policy = "MILITARY_POLICY"
    train.census(g)
    assert g.stock["gold"] == 0                                        # the 2 old kills pay nothing
    n[spoils.UNIT_KILLS] = 3
    train.census(g)
    assert g.stock["gold"] == civs.policy(g)[1]["kill_gold"]


def test_a_mapuche_kill_still_gives_its_gold_and_no_policy_gold():
    server, g = game("MAPUCHE")
    scores(server, **{spoils.OBJECTIVE: 1, spoils.UNIT_KILLS: 1})
    train.census(g)
    assert g.stock["gold"] == civs.KILL_GOLD["MAPUCHE"]
    assert f"scoreboard players get p1 {spoils.UNIT_KILLS}" not in server.log   # no policies: no command


def test_a_trade_unit_gets_the_tag_of_no_policy_gold():
    assert spoils.tag_command("u", "TRADE_CART") == f"tag u add {spoils.TRADE}"
    assert spoils.tag_command("u", "TRADE_COG") == f"tag u add {spoils.TRADE}"
    assert spoils.tag_command("u", "MILITIA") is None


@pytest.mark.mc
def test_the_plugin_counts_the_kills_of_enemy_units_by_infantry(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    get = f"scoreboard players get p1 {spoils.UNIT_KILLS}"
    with run.Game(world) as game:
        floor(game, x0, y, z0, 20)
        game.command(f'summon zombie {x0 + 0.5} {y} {z0 + 2.5} {{IsBaby:0b,Tags:["a"],PersistenceRequired:1b}}')
        game.command("team join p1 @e[tag=a]")
        game.command(combat.stats_command("@e[tag=a,limit=1]", "CHAMPION"))
        for k, (tag, name, extra) in enumerate((("t", "TRADE_CART", spoils.TRADE), ("v", "VILLAGER", None),
                                                ("m", "MILITIA", None))):
            game.command(f'summon zombie {x0 + 3.5} {y} {z0 + 2.5} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join p2 @e[tag={tag}]")
            game.command(combat.stats_command(f"@e[tag={tag},limit=1]", name))
            if extra:
                game.command(f"tag @e[tag={tag},limit=1] add {extra}")
            assert game.command(f"aoe attack @e[tag=a] @e[tag={tag},limit=1]").strip() == "Attack: 1 units"
            end = time.time() + 30
            while time.time() < end and data(game, tag, "Health") is not None:
                time.sleep(0.1)
            assert data(game, tag, "Health") is None, f"the {name} is alive"
            m = re.search(r"has (\d+)", game.command(get))
            assert (int(m[1]) if m else 0) == k, name                 # no point for the trade cart
