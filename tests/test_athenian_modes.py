"""Athenian policies (#2485): the town center of an Athenian player switches between the Economic, Military and Naval
policy (AoE2 wiki "Economic Policy", "Military Policy", "Naval Policy", MediaWiki API, 2026-10-28). Economic is the
start policy: lumberjacks make 50 % more food. Military: barracks, archery ranges, stables and docks cost 33 % less
wood. Naval: foot archers and warships cost 20 % less gold. The first switch is free, then 25 and 50 gold."""
import pytest
from menu_line import item
from test_forging import menus
from test_second_resource import game, loads

from game import build, civs, train


def town_center(civ):
    server, g = game(civ)
    g.stock.update(food=1000, wood=1000, gold=1000)
    rect = next(r for r, n in train.homes(g).items() if n == "TOWN_CENTER")
    return server, g, rect


def switch(g, rect, name):
    assert train.queue(g, "Steve", rect[::2], name), name
    train.tick(g, train.TRAIN_TIMES[name])
    assert civs.policy(g)[0] == name


def menu(server, g, rect):
    train.show(g, "Steve", rect)
    return menus(server)[-1]


def test_an_athenian_player_switches_the_policy_and_pays_the_wiki_gold():
    server, g, rect = town_center("ATHENIANS")
    assert civs.policy(g)[0] == "ECONOMIC_POLICY"
    text = menu(server, g, rect)
    assert item(text, "Economic Policy") is None                       # the active policy is not in the menu
    assert item(text, "Military Policy") == "19:book:Military Policy:free · 15 s · research"
    assert item(text, "Naval Policy") == "20:book:Naval Policy:free · 15 s · research"
    gold = g.stock["gold"]
    switch(g, rect, "NAVAL_POLICY")
    assert g.stock["gold"] == gold and "NAVAL_POLICY" not in g.techs
    text = menu(server, g, rect)
    assert item(text, "Naval Policy") is None
    assert item(text, "Economic Policy") == "18:book:Economic Policy:25 gold · 15 s · research"
    switch(g, rect, "ECONOMIC_POLICY")
    assert g.stock["gold"] == gold - 25
    switch(g, rect, "MILITARY_POLICY")
    switch(g, rect, "NAVAL_POLICY")
    assert g.stock["gold"] == gold - 25 - 50 - 50                      # each later switch: 50 gold


def test_the_policy_changes_the_costs():
    server, g, rect = town_center("ATHENIANS")
    base = {n: train.price(g, n) for n in ("ARCHER", "GALLEY", "MAN_AT_ARMS")} | {"BARRACKS": build.price(g, "BARRACKS")}
    switch(g, rect, "NAVAL_POLICY")
    assert train.price(g, "ARCHER")["gold"] == round(base["ARCHER"]["gold"] * 0.8)
    assert train.price(g, "GALLEY")["gold"] == round(base["GALLEY"]["gold"] * 0.8)
    assert train.price(g, "MAN_AT_ARMS") == base["MAN_AT_ARMS"]
    switch(g, rect, "MILITARY_POLICY")
    assert train.price(g, "ARCHER") == base["ARCHER"]
    assert build.price(g, "BARRACKS")["wood"] == round(base["BARRACKS"]["wood"] * 0.67)
    assert build.price(g, "HOUSE") == build.COSTS["HOUSE"]


def test_the_economic_policy_gives_the_lumberjacks_50_percent_more_food():
    g, side = loads("ATHENIANS", "wood")
    assert side["food"] == pytest.approx(g.stock["wood"] / 9.8, abs=1)  # 1 food for each 9.8 wood
    _, g = game("ATHENIANS")
    g.policy = "MILITARY_POLICY"
    assert civs.extra(g, "wood") == ("food", 0.068)                    # the base bonus: 1 food for each 14.7 wood


def test_another_civilization_does_not_see_the_policies():
    server, g, rect = town_center("SPARTANS")
    text = menu(server, g, rect)
    assert "Policy" not in text and not train.queue(g, "Steve", rect[::2], "NAVAL_POLICY")
    assert civs.policy(g) == (None, {})
