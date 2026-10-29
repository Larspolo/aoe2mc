"""Athenian policies (#2485): the town center of an Athenian player switches between the Economic, Military and Naval
policy (AoE2 wiki "Economic Policy", "Military Policy", "Naval Policy"). Economic is the start policy: lumberjacks make
more food. Military: barracks, archery ranges, stables and docks cost less wood. Naval: foot archers and warships
cost less gold. Each switch costs the gold of the key "policies"."""
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


def text_of(g, name, building=None):
    """The cost and time text of the menu item of name, from the data (as train.show writes it)."""
    return (" · ".join(f"{v} {r}" for r, v in train.price(g, name, building).items()) or "free") + \
        f" · {round(train.seconds(g, name, building), 1):g} s · "


def menu(server, g, rect):
    train.show(g, "Steve", rect)
    return menus(server)[-1]


def test_an_athenian_player_switches_the_policy_and_pays_the_gold_of_the_data():
    server, g, rect = town_center("ATHENIANS")
    assert civs.policy(g)[0] == civs.policies(g)["start"]
    cost = civs.policies(g)["gold"]                                    # the gold of each switch; the last one repeats
    cost = lambda n, c=cost: c[min(n, len(c) - 1)]
    text = menu(server, g, rect)
    assert item(text, "Economic Policy") is None                       # the active policy is not in the menu
    for label in ("Military Policy", "Naval Policy"):
        name = label.upper().replace(" ", "_")
        assert item(text, label).endswith(f":{label}:" + text_of(g, name) + "research")
    gold = g.stock["gold"]
    switch(g, rect, "NAVAL_POLICY")
    assert g.stock["gold"] == gold - cost(0) and "NAVAL_POLICY" not in g.techs
    text = menu(server, g, rect)
    assert item(text, "Naval Policy") is None
    assert item(text, "Economic Policy").endswith(":Economic Policy:" + text_of(g, "ECONOMIC_POLICY") + "research")
    for n, name in enumerate(("ECONOMIC_POLICY", "MILITARY_POLICY", "NAVAL_POLICY"), 1):
        switch(g, rect, name)
        assert g.stock["gold"] == gold - sum(cost(k) for k in range(n + 1)), name


def test_the_policy_changes_the_costs():
    server, g, rect = town_center("ATHENIANS")
    base = {n: train.price(g, n) for n in ("ARCHER", "GALLEY", "MAN_AT_ARMS")} | {"BARRACKS": build.price(g, "BARRACKS")}
    switch(g, rect, "NAVAL_POLICY")
    assert train.price(g, "ARCHER")["gold"] < base["ARCHER"]["gold"]
    assert train.price(g, "GALLEY")["gold"] < base["GALLEY"]["gold"]
    assert train.price(g, "MAN_AT_ARMS") == base["MAN_AT_ARMS"]
    switch(g, rect, "MILITARY_POLICY")
    assert train.price(g, "ARCHER") == base["ARCHER"]
    assert build.price(g, "BARRACKS")["wood"] < base["BARRACKS"]["wood"]
    assert build.price(g, "HOUSE") == build.COSTS["HOUSE"]


def test_the_economic_policy_gives_the_lumberjacks_more_food():
    g, side = loads("ATHENIANS", "wood")
    _, h = game("ATHENIANS")
    h.policy = "MILITARY_POLICY"
    res, base = civs.extra(h, "wood")                                   # the base bonus
    assert res == "food" and side["food"] > g.stock["wood"] * base + 1


def test_another_civilization_does_not_see_the_policies():
    server, g, rect = town_center("SPARTANS")
    text = menu(server, g, rect)
    assert "Policy" not in text and not train.queue(g, "Steve", rect[::2], "NAVAL_POLICY")
    assert civs.policy(g) == (None, {})
