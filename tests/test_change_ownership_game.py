"""#2998 (epic #2991): the units that a "Change Ownership" trigger gives to another player belong to the new owner in
the game program too. The order "owner <tag> <old> <new>" (aoe2mc.owner_lines) reaches scenario.orders, which gives
each tagged unit to the new owner with owners.give (#2993), and removes the tag."""
import numpy as np
from test_scenario_mode import game
from test_scenario_patrol import scenario, trigger

import aoe2mc


def run(order, tagged, players=None):
    """scenario.orders with one stored order. Player 2 (the bot) has the archer b1 and the militia b2 (in the area of the
    order when tagged): b1 and b2 are the units of the old owner. Player 1 has no unit."""
    server, g, bot = game(players or {"1": {}, "2": {}})
    bot.soldiers.update({"b1": "ARCHER", "b2": "MILITIA"})
    g.enemies.update({"b1": "ARCHER", "b2": "MILITIA"})
    g.data["objects"] += [{"kind": "unit", "name": "ARCHER", "player": 2, "uuid": "b1"},
                          {"kind": "unit", "name": "MILITIA", "player": 2, "uuid": "b2"}]
    stored = [f'Storage aoe2mc:orders has the following contents: ["{order}"]']
    command = server.command

    def answer(cmd):
        if cmd.startswith("data remove storage aoe2mc:orders"):
            stored[0] = "Found no elements matching list"
        if cmd.startswith("data get storage aoe2mc:orders"):
            return stored[0]
        return command(cmd)
    server.command = answer
    g.where = lambda want, sel=None: {u: (0.0, 0.0, 0.0) for u in tagged}
    scenario.orders(g)
    return g, bot, server.log


def test_the_tagged_units_of_the_old_owner_go_to_the_new_owner():
    g, bot, log = run("owner aoe_order5_0 2 1", {"b1"})
    assert "b1" in g.soldiers and "b1" not in g.enemies               # player 1 takes the archer as a soldier
    assert "b1" not in bot.soldiers and "b1" in bot.enemies           # the bot is now the enemy of player 1
    assert "b2" in bot.soldiers and "b2" not in g.soldiers            # no tag: the militia stays
    assert next(o for o in g.data["objects"] if o.get("uuid") == "b1")["player"] == 1
    assert log[-1] == "tag @e[tag=aoe_order5_0] remove aoe_order5_0"


def test_gaia_takes_the_units_out_of_every_list_of_the_old_owner():
    g, bot, _ = run("owner aoe_order5_0 2 0", {"b1"})
    assert "b1" not in g.enemies and "b1" not in bot.enemies and "b1" not in bot.soldiers and "b1" not in g.soldiers
    assert next(o for o in g.data["objects"] if o.get("uuid") == "b1")["player"] == 0


def test_the_owner_tag_of_the_trigger_is_stored_in_the_order_line():
    t = trigger(aoe2mc.CHANGE_OWNERSHIP)
    t["effects"][0].update(player=2, target=1, area=[0, 0, 5, 5])
    out = aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16))[1].get(
        "data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()
    assert 'data modify storage aoe2mc:orders list append value "owner aoe_order7_0 2 1"' in out
