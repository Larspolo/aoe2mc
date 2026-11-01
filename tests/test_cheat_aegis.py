"""game/cheats.py: the cheat "aegis" makes building, training, research and gathering instant; a second "aegis" ends
it (#817). Fake server, no Minecraft."""
import lang
from test_build_done import DOWN
from test_build_site import Server
from test_gather import grid
from test_gather_mines import mine_map
from test_gather_rates import ticks_per_load
from test_train import setup

from game import build, cheats, gather, train


def type_code(server, g, code="aegis"):
    server.scores[cheats.OBJECTIVE] = cheats.NAMES.index(code) + 1
    return cheats.clicks(g)


def test_aegis_toggles_and_answers_in_the_chat():
    server, g = setup()
    g.cheats = True
    assert type_code(server, g) == [("Steve", "aegis")] and g.aegis
    assert lang.english(server.log[-1]) == 'tellraw Steve "Aegis on"'
    type_code(server, g)
    assert not g.aegis and lang.english(server.log[-1]) == 'tellraw Steve "Aegis off"'


def test_no_aegis_with_cheats_off():
    server, g = setup()
    assert type_code(server, g) == [] and not g.aegis


def test_a_villager_comes_out_at_the_next_tick():
    server, g = setup(food=100)
    g.cheats = True
    type_code(server, g)
    assert train.queue(g, "Steve", (3, 3))
    g.step()
    assert len(g.villagers) == 2 and not g.queues[2, 5, 2, 5]
    type_code(server, g)                                       # off: the AoE2 train time again
    assert train.queue(g, "Steve", (3, 3))
    g.step()
    assert len(g.villagers) == 2 and g.queues[2, 5, 2, 5][0]["progress"] < 0.1


def test_research_is_instant():
    server, g = setup(food=100)
    g.aegis = True
    g.queues[2, 5, 2, 5] = [{"name": "LOOM", "player": "Steve", "progress": 0.0}]
    train.tick(g, g.tick * gather.NORMAL)
    assert "LOOM" in g.techs and not g.queues[2, 5, 2, 5]


def test_a_load_is_full_after_one_work_step():
    server, g = mine_map()
    slow = ticks_per_load(g, "v", (12, 12))
    server, g = mine_map()
    g.aegis = True
    assert ticks_per_load(g, "v", (12, 12)) == 1 < slow


def house(aegis):
    """Steps from the start of the work until a house of one villager is complete (the site of test_build_done.done)."""
    data = grid([[64] * 48 for _ in range(48)])
    data["objects"].append({"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v0"})
    data.update(tile_size=4, level_height=1, players={"1": {"color": "blue", "arch": "western"}})
    server = Server({"Steve": {"Pos": (9.5, 64.0, 9.5), "Rotation": DOWN}, "v0": {"Pos": (30.5, 64.0, 30.5)}},
                    chosen=build.MENU.index("HOUSE") + 1)
    g = gather.Gather(server, data).setup()
    g.stock.update(wood=500)
    g.aegis = aegis
    g.click("Steve")
    site, = g.sites
    g.select("v0")
    g.click("Steve")
    for n in range(3000):
        if g.villagers["v0"].state == "build":
            break
        g.step()
    for k in range(3000):
        if site["progress"] == 1:
            return k
        g.step()


def test_a_house_is_complete_in_the_tick_of_the_first_work():
    assert house(True) == 0 < house(False)
