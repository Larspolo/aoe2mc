"""#2772 (epic #2538): the trigger effects "Train Unit" and "Initiate Research" put an order for each selected building
into the data storage aoe2mc:orders; the scenario mode of the game program queues it at that building as clicks of its
menu do, and the player pays."""
import os
import sys

import numpy as np

import aoe2mc
from test_civ_costs import setup
from test_scenario_patrol import trigger

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import scenario  # noqa: E402
from game import train  # noqa: E402

STORE = "data modify storage aoe2mc:orders list append value"


def lines(kind, **effect):
    t = trigger(kind)
    t["effects"][0].update(effect)
    return aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16))[1].get(
        "data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_train_unit_stores_one_order_for_each_selected_building():
    assert lines(aoe2mc.TRAIN_UNIT, object=("U", "MILITIA"), quantity=3, selected=[42, 43]) == [
        f'{STORE} "train 42 MILITIA 3"', f'{STORE} "train 43 MILITIA 3"']
    assert lines(aoe2mc.TRAIN_UNIT, object=("U", "MILITIA"), quantity=-1, selected=[42]) == [
        f'{STORE} "train 42 MILITIA 1"']                              # no quantity: one unit


def test_initiate_research_stores_the_technology():
    assert lines(aoe2mc.INITIATE_RESEARCH, technology="LOOM", selected=[41]) == [f'{STORE} "research 41 LOOM"']


def test_no_building_or_no_unit_gives_no_order():
    assert lines(aoe2mc.TRAIN_UNIT, object=("U", "MILITIA"), quantity=3, selected=[]) == []
    assert lines(aoe2mc.TRAIN_UNIT, object=None, quantity=3, selected=[42]) == []
    assert lines(aoe2mc.INITIATE_RESEARCH, technology="LOOM", selected=[41], player=0) == []


def game(**stock):
    """Player 1 (Goths, Feudal Age) with its town center (ref 41) and a barracks (ref 42) of the scenario."""
    _, g = setup("GOTHS", **stock)
    g.data["objects"][0]["ref"] = 41
    g.data["objects"].append({"kind": "building", "name": "BARRACKS", "player": 1, "ref": 42, "footprint": [16, 2, 19, 5]})
    return g


def orders(g, stored):
    """Run scenario.orders with a fake storage that holds the texts of stored; return the RCON log."""
    command, log = g.command, []

    def answer(cmd):
        log.append(cmd)
        if cmd.startswith(f"data get storage {scenario.ORDERS}"):
            return f"Storage {scenario.ORDERS} has the following contents: {stored}"
        return command(cmd)
    g.command = answer
    scenario.orders(g)
    return log


def test_the_order_queues_three_militia_at_the_barracks_and_the_player_pays():
    g = game(food=200, gold=200)
    log = orders(g, '["train 42 MILITIA 3", "research 41 LOOM"]')
    assert f"data remove storage {scenario.ORDERS} list" in log
    assert [q["name"] for q in g.queues[(16, 19, 2, 5)]] == ["MILITIA"] * 3
    assert [q["name"] for q in g.queues[(2, 5, 2, 5)]] == ["LOOM"]
    militia, loom = train.price(g, "MILITIA", "BARRACKS"), train.price(g, "LOOM", "TOWN_CENTER")
    assert g.stock["food"] == 200 - 3 * militia["food"]
    assert g.stock["gold"] == 200 - 3 * militia["gold"] - loom["gold"]


def test_too_few_resources_stop_the_queue_as_in_the_menu():
    g = game(gold=200)
    food = train.price(g, "MILITIA", "BARRACKS")["food"]
    g.stock["food"] = 2 * food + 1
    orders(g, '["train 42 MILITIA 3"]')
    assert len(g.queues[(16, 19, 2, 5)]) == 2 and g.stock["food"] == 1


def test_an_unknown_building_gives_no_queue():
    g = game(food=200, gold=200)
    orders(g, '["train 99 MILITIA 3"]')
    assert not any(g.queues.values()) and g.stock["food"] == 200
