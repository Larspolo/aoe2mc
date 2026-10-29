"""Spies (#2193): the castle researches it (AoE2 DE wiki "Spies": a cost for each enemy civilian unit, with a minimum and
a maximum, train.PER_ENEMY), and then the player sees all enemy units: the fog of war shows the hidden enemy units at
once and hides no unit after it (fog.reveal, fog.tick)."""
from test_hoardings import setup
from test_loom import menus

from game import fog, train

E1, E2 = "00000000-0000-0000-0000-00000000e001", "00000000-0000-0000-0000-00000000e002"


def spies(age=3, enemies=None):
    server, g = setup(age)
    g.enemies = {E1: "VILLAGER_MALE", E2: "MILITIA"} if enemies is None else enemies
    g.stock.update(gold=400)
    return server, g


def cost(names):
    """The gold of Spies for the enemy units names: the cost for each civilian unit of PER_ENEMY, at least once."""
    kinds, most = train.PER_ENEMY["SPIES"]
    n = max(1, sum(any(u.startswith(k) for k in kinds) for u in names))
    return {"gold": min(train.COSTS["SPIES"]["gold"] * n, most["gold"])}


def test_the_cost_is_a_cost_for_each_enemy_civilian_with_a_minimum_and_a_maximum():
    _, g = spies()
    assert train.price(g, "SPIES") == cost(g.enemies.values())
    g.enemies = {f"e{i}": n for i, n in enumerate(["VILLAGER_FEMALE", "TRADE_CART_EMPTY", "FISHING_SHIP", "KNIGHT"])}
    assert train.price(g, "SPIES") == cost(g.enemies.values())
    g.enemies = {}
    assert train.price(g, "SPIES") == cost([]) == train.COSTS["SPIES"]  # the minimum
    g.enemies = {f"e{i}": "VILLAGER_MALE" for i in range(200)}
    assert train.price(g, "SPIES") == cost(g.enemies.values())          # the maximum


def test_the_castle_menu_shows_it_in_its_age():
    slot, item, label = train.slots("CASTLE", "SPIES")
    for age in (2, 3):
        server, g = spies(age)
        train.open_menu(g, "Steve", (12, 4))
        assert (f" {slot}:{item}:{label}:" in menus(server)[-1]) == train.unlocked(g, "SPIES")
    assert train.unlocked(g, "SPIES")                                  # the Imperial Age has it


def test_the_research_shows_the_hidden_enemy_units_and_the_fog_hides_no_more():
    server, g = spies()
    g.paper = True
    vars(g)["fog"] = {"hidden": {E1, E2}, "at": None}
    gold = g.stock["gold"] - train.price(g, "SPIES")["gold"]
    assert train.order(g, "Steve", train.open_menu(g, "Steve", (12, 4)), train.slots("CASTLE", "SPIES")[0]) == 1
    assert g.stock["gold"] == gold
    assert not any(c.startswith("aoe show") for c in server.log)       # not before the research
    train.tick(g, train.TRAIN_TIMES["SPIES"])
    assert "SPIES" in g.techs and f"aoe show @a[team=p1] {E1} {E2}" in server.log
    assert vars(g)["fog"]["hidden"] == set()
    n = len(server.log)
    fog.tick(g)                                                        # no fog: no query of the positions, no hide
    assert server.log[n:] == []
