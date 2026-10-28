"""A unit that a bot or another person trains during a game is an enemy of the other sides (#2992, epic #2991): a right
click on it gives an attack order, a monk converts it, and Faith and Heresy of its owner count. Fake server of
test_gather."""
import numpy as np

from test_gather import FakeServer, grid

from game import bot, gather, herd, monk, run, train

MAP = [[64] * 24 for _ in range(24)]


def objects():
    return [{"kind": "unit", "name": "MILITIA", "player": 1, "uuid": "m-1", "tile": [2.5, 2.5]},
            {"kind": "unit", "name": "MONK", "player": 1, "uuid": "monk-1", "tile": [3.5, 2.5]},
            {"kind": "unit", "name": "MILITIA", "player": 2, "uuid": "m-2", "tile": [12.5, 12.5]}]


def with_bot(teams=None):
    """Player 1 and a bot of player 2 on one data of aoe2mc.json (run.play); teams: {player: team}."""
    data = grid(MAP, objects())
    for p, t in (teams or {}).items():
        data.setdefault("players", {}).setdefault(str(p), {})["team"] = t
    server = FakeServer({"m-1": {"Pos": (2.5, 64.0, 2.5)}, "monk-1": {"Pos": (3.5, 64.0, 2.5)}})
    g = gather.Gather(server, data).setup()
    b = bot.Bot(server, data, share=g, start={}).setup()
    g.bots = [b]
    return server, g, b


def trained(server, side, name="MILITIA"):
    uuid = train.summon(side, name, (13.5, 64.0, 15.5))
    server.entities[uuid] = {"Pos": (13.5, 64.0, 15.5)}
    return uuid


def test_a_militia_that_the_bot_trains_is_an_enemy_of_player_1():
    server, g, b = with_bot()
    uuid = trained(server, b.g)
    g.select("m-1")
    eye = (13.5, 65.0, 19.5)                                           # 4 blocks south of it, at its body height
    assert g.target(eye, gather.direction(180, 0), g.positions(sorted(g.pickable())))[:2] == ("enemy", uuid)
    assert g.enemies[uuid] == "MILITIA" and uuid not in b.g.enemies
    assert monk.convert_order(g, ["monk-1"], uuid)


def test_a_unit_that_an_ally_trains_is_no_enemy():
    server, g, b = with_bot({1: 1, 2: 1})
    uuid = trained(server, b.g)
    assert uuid not in g.enemies and uuid not in b.g.enemies


def test_a_unit_of_one_person_is_an_enemy_of_the_other_person():
    server = FakeServer({})
    data = grid(MAP, objects())
    g, g2 = gather.Gather(server, data).setup(), gather.Gather(server, data, player=2).setup()
    g.bots = [run.Side(g2)]
    g2.peers = [g]
    mine, theirs = train.summon(g, "MILITIA", (2.5, 64.0, 5.5)), train.summon(g2, "MILITIA", (13.5, 64.0, 15.5))
    assert theirs in g.enemies and mine in g2.enemies
    assert mine not in g.enemies and theirs not in g2.enemies


def test_a_monk_converts_a_trained_unit_of_the_bot():
    server, g, b = with_bot()
    uuid = trained(server, b.g)
    b.g.techs.add("FAITH")
    assert monk.resist(g, uuid) == monk.RESIST["FAITH"] == monk.resist(g, "m-2")
    server.log.clear()
    monk.take(g, uuid)
    assert f"tag {uuid} remove aoe2mc.p2" in server.log and f"tag {uuid} add aoe2mc.p1" in server.log


def test_heresy_of_the_bot_kills_its_trained_unit():
    server, g, b = with_bot()
    uuid = trained(server, b.g)
    b.g.techs.add("HERESY")
    g.converting["monk-1"] = [uuid, 0.0, 99]                           # the last interval: it converts now
    g.chance = np.random.default_rng(1)
    server.entities[uuid] = {"Pos": (3.5, 64.0, 4.5)}                  # next to the monk
    server.log.clear()
    monk.convert(g, monk.INTERVAL)
    assert f"kill {uuid}" in server.log and uuid not in g.enemies
    assert not any(c.startswith(f"tag {uuid}") for c in server.log)


def test_a_tatar_sheep_of_the_bot_is_an_enemy_of_player_1():
    server, g, b = with_bot()
    herd.spawn(b.g, (12, 14, 12, 14), "SHEEP", 1)
    sheep = next(u for u, n in b.g.prey.items() if n == "SHEEP")
    assert g.enemies[sheep] == "SHEEP" and sheep not in b.g.enemies
