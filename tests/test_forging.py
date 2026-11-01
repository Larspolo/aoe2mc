"""game/build.py and game/train.py: the blacksmith menu has "Forging". A click queues it once; after the research the
infantry and cavalry of the player have more attack, also the new ones, and the item leaves the menu (#675)."""
from urllib.parse import unquote

import lang
from test_gather import FakeServer, grid

from game import combat, gather, train


def entry(g, name, state):
    """The menu item of name with its cost and time for the player of g."""
    slot, item, label = train.ITEMS[name]
    cost = " · ".join(f"{v} {k}" for k, v in train.COSTS[name].items())
    return f"{slot}:{item}:{label}:{cost} · {train.seconds(g, name):g} s · {state}"


# .get: the Antiquity rules have no Forging, and their tests import setup() from here
COST, SLOT = train.COSTS.get("FORGING", {}).get("food", 0), train.ITEMS.get("FORGING", (None,))[0]


def setup(food=COST, age=1):
    """A flat 24 × 24 map (tile size 1): a town center of player 1 at blocks x 2-4, z 2-4, a barracks at x 16-18,
    z 2-4, a built blacksmith at x 10-12, z 2-4, a villager, a militia, a scout and an archer."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "building", "name": "BARRACKS", "player": 1, "tile": [17.5, 3.5], "footprint": [16, 2, 19, 5]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [7.5, 7.5]},
               {"kind": "unit", "name": "MILITIA", "player": 1, "uuid": "m", "tile": [9.5, 9.5]},
               {"kind": "unit", "name": "SCOUT_CAVALRY", "player": 1, "uuid": "s", "tile": [11.5, 11.5]},
               {"kind": "unit", "name": "ARCHER", "player": 1, "uuid": "a", "tile": [13.5, 13.5]}]
    server = FakeServer({u: {"Pos": (p, 64.0, p)} for u, p in (("v", 7.5), ("m", 9.5), ("s", 11.5), ("a", 13.5))})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()
    g.sites.append({"name": "BLACKSMITH", "player": 1, "footprint": [10, 13, 2, 5], "done": True})
    g.stock.update(food=food)
    g.techs.update({"FEUDAL_AGE"} if age else ())                   # a Feudal Age technology (the key "age", #1046)
    return server, g


def menus(server):
    """The menu commands of the log; a long menu with its `aoe menu-add` parts as one text (#1647)."""
    out = []
    for c in server.log:
        if c.startswith("aoe menu "):
            out.append(unquote(c))
        elif c.startswith("aoe menu-add ") and out:
            out[-1] += " " + unquote(c.split(" ", 4)[4])
    return out


def test_the_blacksmith_menu_has_forging():
    server, g = setup()
    train.open_menu(g, "Steve", (11, 3))
    assert f" {entry(g, 'FORGING', 'research')} " in menus(server)[0] + " "


def test_a_click_queues_forging_once_and_takes_its_cost():
    server, g = setup(food=1000)
    rect = train.open_menu(g, "Steve", (11, 3))
    assert train.order(g, "Steve", rect, SLOT, shift=True) == 1 and g.stock["food"] == 1000 - COST
    assert train.order(g, "Steve", rect, SLOT) == 0 and g.stock["food"] == 1000 - COST
    assert f"scoreboard players remove Food aoe_res {COST}" in server.log
    assert f" {entry(g, 'FORGING', 'researching')} " in menus(server)[-1] + " "


def test_forging_gives_infantry_and_cavalry_more_attack():
    server, g = setup()
    rect = train.open_menu(g, "Steve", (11, 3))
    train.order(g, "Steve", rect, SLOT)
    train.tick(g, train.TRAIN_TIMES["FORGING"] - 1)
    assert g.techs == {"FEUDAL_AGE"} and not [c for c in server.log if c.startswith("aoe stats")]
    train.tick(g, 1)
    assert g.techs == {"FEUDAL_AGE", "FORGING"} and not any(g.queues.values())
    for name in ("MILITIA", "SCOUT_CAVALRY", "SPEARMAN", "KNIGHT", "CAMEL_RIDER", "WAR_ELEPHANT"):
        s, t = combat.stats(name), train.stats(g, name)
        assert t.attack > s.attack and t == s._replace(attack=t.attack), name
    for name in ("VILLAGER_MALE", "ARCHER", "CAVALRY_ARCHER", "MANGONEL", "MONK"):
        assert train.stats(g, name) == combat.stats(name), name
    stats = sorted(c for c in server.log if c.startswith("aoe stats"))
    assert stats == sorted(combat.stats_command(u, n, train.stats(g, n)) for u, n in (("m", "MILITIA"), ("s", "SCOUT_CAVALRY")))
    assert any("Forging is researched." in c for c in map(lang.english, server.log) if c.startswith("tellraw"))
    train.open_menu(g, "Steve", (11, 3))
    assert "Forging" not in menus(server)[-1]
    assert train.queue(g, "Steve", (11, 3), "FORGING") is None        # only once


def test_forging_and_loom_together():
    server, g = setup()
    g.techs.update({"FORGING", "LOOM"})
    assert train.stats(g, "MILITIA").attack > combat.stats("MILITIA").attack
    assert train.stats(g, "VILLAGER_MALE").hp > combat.stats("VILLAGER_MALE").hp


def test_a_new_militia_has_the_forging_attack():
    cost = train.COSTS["MILITIA"]
    server, g = setup(food=cost.get("food", 0))
    g.stock.update(gold=cost.get("gold", 0))
    g.techs.add("FORGING")
    assert train.queue(g, "Steve", (17, 3), "MILITIA")
    uuid, = train.tick(g, train.seconds(g, "MILITIA"))
    assert combat.stats_command(uuid, "MILITIA", train.stats(g, "MILITIA")) in server.log
    assert train.stats(g, "MILITIA").attack > combat.stats("MILITIA").attack
