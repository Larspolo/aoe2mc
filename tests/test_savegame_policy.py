"""A saved game keeps the active policy of an Athenian player and the number of its switches (#2515, epic #2253): after
the load the policy is the same, and the next switch costs the same gold."""
import json

from test_athenian_modes import switch, town_center

from game import civs, savegame, train


def test_a_loaded_game_has_the_policy_and_the_gold_of_the_next_switch():
    _, g, rect = town_center("ATHENIANS")
    switch(g, rect, "NAVAL_POLICY")
    _, h, _ = town_center("ATHENIANS")
    savegame.load(h, json.loads(json.dumps(savegame.dump(g), sort_keys=True)))
    assert civs.policy(h)[0] == "NAVAL_POLICY"
    first = train.price(town_center("ATHENIANS")[1], "MILITARY_POLICY")       # a game with no switch
    assert train.price(h, "MILITARY_POLICY") == train.price(g, "MILITARY_POLICY") != first


def test_a_game_without_a_switch_gives_no_new_keys():
    _, g, _ = town_center("ATHENIANS")
    p = savegame.dump(g)["players"]["1"]
    assert "policy" not in p and "switches" not in p
