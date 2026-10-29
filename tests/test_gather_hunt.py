"""game/gather.py: villagers hunt deer, boars and herdables, and the cheat aegis kills a hunted animal at once (#1058)."""
import re

import pytest

from game import gather

from test_gather import FakeServer, grid

HP = {"DEER": 20.0, "WILD_BOAR": 20.0, "SHEEP": 8.0}                    # vanilla health of the horse, panda and sheep


class Hunt(FakeServer):
    """FakeServer with `damage`: an entity at 0 health is dead (no Pos)."""

    def command(self, cmd):
        out = super().command(cmd)
        if m := re.fullmatch(r"damage (\S+) (\d+) minecraft:mob_attack by (\S+)", cmd):
            e = self.entities.get(m[1])
            if e:
                e["Health"] = e.get("Health", 20.0) - int(m[2])
                if e["Health"] <= 0:
                    del self.entities[m[1]]
        return out


def game(animal="DEER", player=0, aegis=False):
    """A villager of player 1 at (2, 2), the animal at (8, 2) and a town center at (2..5, 8..11), tile size 1."""
    objects = [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [2.5, 2.5]},
               {"kind": "unit", "name": animal, "player": player, "uuid": "a", "tile": [8.5, 2.5]},
               {"kind": "building", "name": "TOWN_CENTER", "player": 1, "footprint": [2, 8, 6, 12]}]
    server = Hunt({"v": {"Pos": (2.5, 64.0, 2.5)}, "a": {"Pos": (8.5, 64.0, 2.5), "Health": HP[animal]}})
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)], objects), tick=0.25, carry=10, start={}).setup()
    g.aegis = aegis
    g.select("v")
    return server, g


def food(server):
    return sum(int(c.split()[-1]) for c in server.log if c.startswith("scoreboard players add Food aoe_res"))


@pytest.mark.parametrize("animal,player", [("DEER", 0), ("WILD_BOAR", 0), ("SHEEP", 1)])
def test_a_villager_kills_the_animal_and_carries_its_food_to_the_town_center(animal, player):
    server, g = game(animal, player)
    assert "a" in g.pickable()                                         # a villager is selected: the animal takes a click
    g.hunt("a")
    v = g.villagers["v"]
    assert v.state == "to_prey" and v.job == "butcher"                 # the hunter look
    hits = steps = 0
    for steps in range(1, 4001):
        g.step()
        hits = sum(c.startswith("damage a 3 minecraft:mob_attack by v") for c in server.log)
        if food(server) >= 20:
            break
    assert "a" not in server.entities and hits == -(-HP[animal] // 3)   # the vanilla health in hits of 3
    lost = gather.HUNT_FOOD[animal] - food(server) - v.load - g.map.carcasses[(8, 2)]   # the decay (#2310)
    assert food(server) >= 20 and list(g.map.carcasses) == [(8, 2)]
    assert 0 < lost <= gather.DECAY[animal] * steps * g.tick * gather.NORMAL
    assert any(c == "scoreboard players add Food aoe_res 10" for c in server.log)
    drops = set().union(*g.map.drops["food"])                          # it carried the food to the town center
    assert any(max(abs(v.cell[0] - a), abs(v.cell[1] - b)) <= 1 for a, b in drops) or v.state != "idle"


def test_the_hits_come_once_per_villager_reload():
    server, g = game()
    g.hunt("a")
    while g.villagers["v"].state != "hunt":
        g.step()
    n = len(server.log)
    for _ in range(round(gather.VILLAGER_HIT[1] / gather.NORMAL / g.tick) * 2):
        g.step()
    assert sum(c.startswith("damage a ") for c in server.log[n:]) == 2


def test_aegis_kills_the_animal_at_the_first_hit():
    server, g = game(aegis=True)
    g.hunt("a")
    while "a" in server.entities:
        g.step()
    assert [c for c in server.log if c.startswith("damage ")] == ["damage a 1000 minecraft:mob_attack by v"]
    for _ in range(3):
        g.step()
    assert g.map.carcasses[(8, 2)] < gather.HUNT_FOOD["DEER"]           # aegis gathers a full load at once


def test_a_click_on_the_animal_sends_the_villager_to_hunt():
    server, g = game()
    eye = (8.5, 65.0, 6.5)                                             # 4 blocks south of the deer, at its body height
    kind, key, _ = g.target(eye, gather.direction(180, 0), g.positions(sorted(g.pickable())))
    assert (kind, key) == ("prey", "a") and g.says(kind, key) == "Deer · Right click: hunt"
    server.entities["Steve"] = {"Pos": (8.5, 63.38, 6.5), "Rotation": (180.0, 0.0)}
    g.click("Steve")
    assert g.villagers["v"].state == "to_prey" and g.villagers["v"].prey == "a"


def test_food_of_the_animals():
    assert all(gather.hunt_food(n) == gather.HUNT_FOOD[n] > 0 for n in ("SHEEP", "DEER", "WILD_BOAR"))
    assert gather.hunt_food("COW_B") == gather.HUNT_FOOD["COW"]         # each cow color has the food of a cow
    assert gather.hunt_food("WOLF") == gather.hunt_food("VILLAGER_MALE") == 0


def test_an_enemy_sheep_and_a_wolf_are_no_prey():
    _, g = game("SHEEP", player=2)
    assert "a" not in g.prey and "a" not in g.pickable()


@pytest.mark.mc
def test_a_villager_hunts_a_deer_and_aegis_kills_a_sheep_on_paper(tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    import contextlib
    import io
    import json
    import time

    import aoe2mc
    from game import run
    m = {"size": 16, "terrain": [[0] * 16 for _ in range(16)], "players": {"1": {"civ": "Britons"}},
         "objects": [{"name": "TOWN_CENTER", "player": 1, "x": 4, "y": 4},
                     {"name": "VILLAGER_MALE", "player": 1, "x": 8.5, "y": 8.5},
                     {"name": "DEER", "player": 0, "x": 11.5, "y": 8.5},
                     {"name": "SHEEP", "player": 1, "x": 8.5, "y": 12.5}]}
    (tmp_path / "m.json").write_text(json.dumps(m))
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(str(tmp_path / "m.json"), str(tmp_path / "W"))
    data = json.load(open(tmp_path / "W" / "aoe2mc.json"))
    data["players"]["1"]["civ"] = "JURCHENS"                          # no decay (#2310): the villager gets all the food
    deer, sheep = (next(o["uuid"] for o in data["objects"] if o["name"] == n) for n in ("DEER", "SHEEP"))
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        end = time.time() + 60                                         # entities load in other threads
        while not (g := gather.Gather(game, data, tick=0.05, carry=10, chop=0.01, start={}).setup()).villagers:
            assert time.time() < end, "the villager did not load"
            time.sleep(1)
        uuid, = g.villagers
        g.select(uuid)
        g.hunt(deer)
        assert 'profession: "minecraft:butcher"' in game.command(f"data get entity {uuid} VillagerData")
        end = time.time() + 240
        while not g.map.carcasses or any(g.map.carcasses.values()) or g.villagers[uuid].state != "idle":
            assert time.time() < end, f"the hunt did not end: {g.villagers[uuid].state} {g.map.carcasses}"
            g.step()
        assert "passed" not in game.command(f"execute if entity {deer}")
        assert f"has {gather.HUNT_FOOD['DEER']} " in game.command("scoreboard players get Food aoe_res")
        sent, command = [], game.command
        game.command = lambda c: sent.append(c) or command(c)
        g.aegis = True
        g.hunt(sheep)
        end = time.time() + 60
        while "passed" in command(f"execute if entity {sheep}"):
            assert time.time() < end, "the sheep did not die"
            g.step()
        game.command = command
        assert [c for c in sent if c.startswith("damage ")] == [f"damage {sheep} 1000 minecraft:mob_attack by {uuid}"]
