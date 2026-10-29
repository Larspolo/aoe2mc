"""game/cheats.py: the cheats "woof woof", "my cpu can handle it", "tech tech one two free", "going above and beyond"
and "noui" (#968). Only with cheats on."""
import pytest
import test_double_bit_axe
from test_castle_upgrades import entry
from test_gather import FakeServer, grid

from game import cheats, gather, hints, train


def typed(server, g, code):
    """The player Steve types code in the chat; returns the commands that follow."""
    server.scores["aoe_cheat"] = cheats.NAMES.index(code) + 1
    server.log.clear()
    g.clicks()
    return list(server.log)


def lumber(**stock):
    """The lumber camp of test_double_bit_axe, with cheats on."""
    server, g = test_double_bit_axe.setup(**stock)
    g.cheats = True
    return server, g


def test_woof_woof_turns_the_birds_into_stormy_dogs():
    objects = [{"kind": "unit", "name": "MACAW", "player": 0, "uuid": "bird", "tile": [5.5, 5.5]},
               {"kind": "unit", "name": "SHEEP", "player": 0, "uuid": "sheep", "tile": [8.5, 8.5]}]
    server = FakeServer({"bird": {"Pos": (5.5, 70.0, 5.5)}, "sheep": {"Pos": (8.5, 64.0, 8.5)}})
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)], objects), cheats=True).setup()
    log = typed(server, g, "woof woof")
    assert [c.split()[1] for c in log if c.startswith("summon ")] == ["minecraft:wolf"]
    assert next(c for c in log if c.startswith("summon ")).split()[2:5] == ["5.5", "64.0", "5.5"]   # on the ground
    assert "tp bird 5.5 -200 5.5" in log and not any("sheep" in c for c in log)
    assert [o["name"] for o in g.data["objects"]] == ["STORMY_DOG", "SHEEP"] and g.data["objects"][0]["uuid"] != "bird"


def test_my_cpu_can_handle_it_raises_the_limit_to_1000():
    server, g = lumber()
    assert train.max_pop(g) == train.LIMIT == 200
    typed(server, g, "my cpu can handle it")
    assert train.max_pop(g) == 1000
    g.data["objects"] += [{"kind": "building", "name": "CASTLE", "player": 1, "footprint": [0, 0, 1, 1]}] * 30
    assert train.limit(g) == 600


def test_tech_tech_one_two_free_makes_technologies_free():
    server, g = lumber(food=0, wood=0)
    assert train.queue(g, "Steve", (3, 3), "DOUBLE_BIT_AXE") is None
    typed(server, g, "tech tech one two free")
    rect = train.open_menu(g, "Steve", (3, 3))
    assert test_double_bit_axe.menus(server)[-1].endswith(entry(g, (3, 3), "DOUBLE_BIT_AXE") + "research")
    assert ":free · " in entry(g, (3, 3), "DOUBLE_BIT_AXE")
    assert train.queue(g, "Steve", (3, 3), "DOUBLE_BIT_AXE") == rect and (g.stock["food"], g.stock["wood"]) == (0, 0)
    assert train.cancel(g, "Steve", rect, 0) == "DOUBLE_BIT_AXE" and (g.stock["food"], g.stock["wood"]) == (0, 0)
    assert train.price(g, "VILLAGER_MALE") == train.COSTS["VILLAGER_MALE"]   # units still cost


def test_going_above_and_beyond_stacks_double_bit_axe():
    server, g = lumber(food=1000, wood=1000)
    before = g.work_time("wood")
    train.queue(g, "Steve", (3, 3), "DOUBLE_BIT_AXE")
    train.tick(g, train.TRAIN_TIMES["DOUBLE_BIT_AXE"])
    assert train.queue(g, "Steve", (3, 3), "DOUBLE_BIT_AXE") is None    # once without the cheat
    once = g.work_time("wood")
    typed(server, g, "going above and beyond")
    assert train.queue(g, "Steve", (3, 3), "DOUBLE_BIT_AXE") is not None
    train.tick(g, train.TRAIN_TIMES["DOUBLE_BIT_AXE"])
    assert train.count(g, "DOUBLE_BIT_AXE") == 2 and g.repeats == {"DOUBLE_BIT_AXE": 1}
    assert g.work_time("wood") == pytest.approx(once * once / before)   # the factor of one research, twice
    train.open_menu(g, "Steve", (3, 3))
    assert "Double-Bit Axe" in test_double_bit_axe.menus(server)[-1]
    g.repeats["DOUBLE_BIT_AXE"] = train.REPEAT - 1
    assert not train.repeatable(g, "DOUBLE_BIT_AXE") and not train.repeatable(g, "FEUDAL_AGE")   # an age stays once


def test_beyond_stacks_combat_technologies():
    server, g = lumber()
    g.techs, g.beyond = set(), True
    base = train.stats(g, "VILLAGER_MALE")
    g.techs = {"LOOM"}
    once = train.stats(g, "VILLAGER_MALE")
    g.repeats = {"LOOM": 2}
    assert train.stats(g, "VILLAGER_MALE").hp == once.hp + 2 * (once.hp - base.hp)


def test_noui_hides_the_interface_and_a_second_noui_shows_it():
    server, g = lumber()
    log = typed(server, g, "noui")
    assert "scoreboard objectives setdisplay sidebar" in log and f"bossbar set aoe2mc:sel_p{g.player} players" in log
    server.log.clear()
    hints.tick(g)
    assert not server.log
    log = typed(server, g, "noui")
    assert f"scoreboard objectives setdisplay sidebar {g.board}" in log
    assert f"bossbar set aoe2mc:sel_p{g.player} players @a" in log and not g.noui


def test_no_effect_with_cheats_off():
    server, g = test_double_bit_axe.setup(food=0, wood=0)
    for code in ("my cpu can handle it", "tech tech one two free", "going above and beyond", "noui", "woof woof"):
        assert not [c for c in typed(server, g, code) if "setdisplay" in c or c.startswith(("summon", "tellraw"))]
    assert (g.pop_cap, g.free_techs, g.beyond, g.noui) == (None, False, False, False)
