"""#2688 (epic #2263): each player of a Battle Royale game starts with Attila the Hun and Alaric the Goth (AoE2 wiki
"BR Fall of Rome"), heroes that regenerate hit points and that a monk cannot convert."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import battle_royale  # noqa: E402
import combat  # noqa: E402
import gather  # noqa: E402
import monk  # noqa: E402
import regen  # noqa: E402
import run  # noqa: E402
from test_gather import FakeServer, grid  # noqa: E402

HEROES = run.MODES["battle-royale"]["heroes"]


def game():
    """Player 1 with a town center, player 2 with only a unit, player 3 with Attila of the scenario, and Gaia."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "footprint": [2, 2, 6, 6]},
               {"kind": "building", "name": "TOWN_CENTER", "player": 0, "footprint": [12, 2, 16, 6]},
               {"kind": "unit", "name": "MILITIA", "player": 2, "uuid": "m-2", "tile": [14.5, 14.5]},
               {"kind": "unit", "name": "ATTILA", "player": 3, "uuid": "a-3", "tile": [3.5, 14.5], "hero": True}]
    g = gather.Gather(FakeServer({"Steve": {}}), grid([[64] * 20 for _ in range(20)], objects)).setup()
    g.players = g.data["players"] = {str(p): {"color": "blue", "arch": "western"} for p in (0, 1, 2, 3)}
    return g


def summoned(g):
    """(name, player) of each hero that heroes() added to the objects."""
    return sorted((o["name"], o["player"]) for o in g.data["objects"] if o.get("hero") and o["uuid"] != "a-3")


def test_each_player_gets_attila_and_alaric_with_their_values():
    g = game()
    battle_royale.heroes(g)
    assert summoned(g) == sorted((h, p) for h in HEROES for p in (1, 2, 3)
                                 if (h, p) != ("ATTILA", 3))           # not Gaia; player 3 keeps its own Attila
    heroes = [o for o in g.data["objects"] if o.get("hero") and o["uuid"] != "a-3"]
    assert all(combat.stats_command(o["uuid"], o["name"]) in g.game.log for o in heroes)   # hit points and attack
    own = {u for u, n in g.soldiers.items() if n in HEROES}           # the heroes of player 1 take orders
    assert len(own) == len(HEROES)


def test_the_heroes_stand_next_to_the_town_center():
    g = game()
    battle_royale.heroes(g)
    pos = {o["player"]: o["tile"] for o in g.data["objects"] if o.get("hero") and o["name"] == "ATTILA"}
    assert 1 <= pos[1][0] <= 7 and 6 <= pos[1][1] <= 8                 # south of the footprint 2..6
    assert abs(pos[2][0] - 14) <= 2 and abs(pos[2][1] - 14) <= 3        # next to the militia of player 2


def test_a_hero_regenerates_its_hit_points_per_minute():
    g = game()
    g.soldiers = {"h-1": "ATTILA", "k-1": "KNIGHT"}
    hp = {"h-1": 300.0, "k-1": 50.0}

    def answer(cmd):
        g.game.log.append(cmd)
        u = cmd.split()[3] if cmd.startswith("data get entity") else cmd.split()[1]
        if cmd.startswith("data get entity"):
            return f"{u} has the following entity data: {hp[u]}f"
        if cmd.startswith("attribute"):
            return f"Attribute value of max_health for {u} is {combat.STATS[g.soldiers[u]].hp}.0"
        return ""
    g.command = answer
    for _ in range(12):                                                 # one AoE2 minute in steps of 5 s
        regen.heroes(g, 5.0)
        hp.update({c.split()[3]: float(c.split()[-1][:-1]) for c in g.game.log if c.startswith("data modify entity")})
    assert hp == {"h-1": 300.0 + combat.REGEN["ATTILA"], "k-1": 50.0}   # a knight does not regenerate
    top = combat.STATS["ATTILA"].hp
    hp["h-1"] = top - 1.0
    regen.heroes(g, 60.0)
    assert g.game.log[-1] == f"data modify entity h-1 Health set value {float(top)}f"   # never more than its max_health


def test_a_monk_cannot_convert_a_spawned_hero():
    g = game()
    battle_royale.heroes(g)
    uuid = next(o["uuid"] for o in g.data["objects"] if o.get("hero") and o["player"] == 2)
    assert not monk.convertible(g, uuid)
    assert monk.convertible(g, "m-2")                                   # the militia of player 2 is no hero
