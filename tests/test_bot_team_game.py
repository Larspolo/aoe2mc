"""#4433: a game of 4 players with 3 bots in 2 teams on the fake server of test_gather (criterion 2 of epic #4017):
each bot gathers, no bot attacks an ally, and the game ends when one team is out."""
import re

from test_conquest import check, live
from test_gather import FakeServer, grid

from game import bot, gather, run

TEAMS = {"0": {}, "1": {"team": 1}, "2": {"team": 2}, "3": {"team": 1}, "4": {"team": 2}}
CORNERS = {1: (2, 2), 2: (24, 24), 3: (2, 24), 4: (24, 2)}


def team_game():
    """A flat 40 × 40 map: a town center and a villager in each corner, a militia of each bot, wood, food, gold and
    stone near each bot. Player 1 is a person and stays idle; players 2, 3 and 4 are bots (run.bot_seats)."""
    objects, pos = [], {}
    for p, (x, z) in CORNERS.items():
        objects.append({"kind": "building", "name": "TOWN_CENTER", "player": p, "footprint": [x, z, x + 3, z + 3]})
        for i in range(1 if p == 1 else 3):
            u = f"v{p}{i}"
            objects.append({"kind": "unit", "name": "VILLAGER_FEMALE", "player": p, "uuid": u, "tile": [x + 4.5, z + 0.5 + i]})
            pos[u] = {"Pos": (x + 4.5, 64.0, z + 0.5 + i)}
        if p > 1:
            for name, dx, dz in (("TREE_OAK", 7, 1), ("FRUIT_BUSH", 1, 6), ("GOLD_MINE", 7, 5), ("STONE_MINE", 5, 7)):
                objects.append({"kind": "other", "name": name, "player": 0, "tile": [x + dx + 0.5, z + dz + 0.5]})
    server = FakeServer(pos)
    command = server.command

    def alive(cmd):                                                    # the targets of the soldiers (test_bot_attack)
        if m := re.fullmatch(r"execute if entity ([0-9a-z]+)", cmd):
            return "Test passed" if m[1] in server.entities else "Test failed"
        return command(cmd)
    server.command = alive
    data = grid([[64] * 40 for _ in range(40)], objects)
    data.update(level_height=1, players={k: dict(v, color="blue", arch="western") for k, v in TEAMS.items()})
    me = gather.Gather(server, data, carry=10, chop=0.05, start={}).setup()
    me.players = data["players"]
    bots = []
    for p, foe in run.bot_seats(TEAMS, 1, "all"):
        b = bot.Bot(server, data, player=p, foe=foe, share=me, attack=0.0, group=1, carry=10, chop=0.05, start={}).setup()
        b.g.players = data["players"]
        b.g.seen_tiles = lambda *a, **k: {(x, z) for x in range(40) for z in range(40)}
        u = f"m{p}"
        x, z = CORNERS[p]
        server.entities[u] = {"Pos": (x + 0.5, 64.0, z + 5.5), "Rotation": (0.0, 0.0)}
        b.g.soldiers[u] = "MILITIA"
        bots.append(b)
    me.bots = bots
    return server, me, bots


def test_the_seats_are_the_three_bots():
    server, me, bots = team_game()
    assert [b.g.player for b in bots] == [2, 3, 4]
    assert all(b.g.villagers and not set(b.g.villagers) & set(me.villagers) for b in bots)


def test_each_bot_gathers():
    server, me, bots = team_game()
    for _ in range(1500):
        for b in bots:
            b.step()
        if all(sum(b.g.stock.values()) for b in bots):
            break
    assert all(sum(b.g.stock.values()) > 0 for b in bots), [b.g.stock for b in bots]


def test_no_bot_attacks_an_ally():
    server, me, bots = team_game()
    side = {}                                                          # unit -> its player, also trained units
    for _ in range(400):
        for b in bots:
            b.step()
        for h in [me, *(b.g for b in bots)]:
            side.update({u: h.player for u in [*h.villagers, *h.soldiers]})
    attacks = [c.split()[2:4] for c in server.log if c.startswith("aoe attack ")]
    assert attacks
    for unit, target in attacks:
        assert target in side and not gather.allied(TEAMS, side[unit], side[target]), (unit, target)


def test_the_game_ends_when_one_team_is_out():
    server, me, bots = team_game()
    me.players = dict(TEAMS)
    live(server, {1, 2, 3, 4})
    check(me)
    assert not me.ended
    live(server, {1, 3})                                               # the units of players 2 and 4 are gone
    check(me)
    assert me.defeated == {2, 4} and me.ended == "Victory"
    assert bots[1].g.ended == "Victory"                                 # the bot of player 3, the ally
