"""A Gaia unit that is not an animal joins the first player whose unit comes near it (#5108). A fake RCON gives the
positions, as tests/test_herd_capture.py."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import gaia  # noqa: E402
import gather  # noqa: E402
import owners  # noqa: E402
import savegame  # noqa: E402
from test_lang_orders import plain_log

T = 4
GAIA, SHEEP, DEER = "00000000-0000-0000-0000-0000000000a1", "00000000-0000-0000-0000-0000000000a2", \
    "00000000-0000-0000-0000-0000000000a3"
VILL, MILITIA = "00000000-0000-0000-0000-000000000001", "00000000-0000-0000-0000-000000000002"
PLAYERS = {"1": {"color": "blue"}, "2": {"color": "red"}}


def bare(player, objects, **kw):
    g = gather.Gather.__new__(gather.Gather)
    g.player, g.data, g.map, g.paper, g.players = player, {"objects": objects}, types.SimpleNamespace(T=T), True, PLAYERS
    g.villagers, g.soldiers, g.selected, g.dead, g.bots, g.peers = {}, {}, set(), {}, [], []
    g.units, g.farmers, g.ships, g.prey, g.enemies, g.flock = [], {}, {}, {}, {}, set()
    g.sent, g.now = [], 0.0
    g.command, g.clock = g.sent.append, lambda: g.now
    g.others = lambda: set()
    vars(g).update(kw)
    return g


def game(gaia_at=(10.0, 10.0), objects=None, **extra):
    """Player 1 with a villager at tile (10, 10), its bot (player 2) with a militia far away, and a Gaia militia."""
    objects = objects or [{"kind": "unit", "name": "MILITIA", "player": 0, "uuid": GAIA, "tile": list(gaia_at), **extra}]
    g = bare(1, objects, villagers={VILL: None})
    b = bare(2, objects, soldiers={MILITIA: "MILITIA"}, share=g)
    g.bots = [types.SimpleNamespace(g=b)]
    for x in (g, b):
        x.enemies = {o["uuid"]: o["name"] for o in objects}
    pos = {VILL: (10 * T, 70.0, 10 * T), MILITIA: (200.0, 70.0, 200.0)}
    g.where = lambda want: {u: p for u, p in pos.items() if u in want}
    return g, b, pos, objects


def test_a_gaia_militia_next_to_a_villager_goes_to_player_1():
    g, b, _, objects = game()
    gaia.tick(g)
    assert objects[0]["player"] == 1 and owners.player(g, GAIA) == 1
    assert g.soldiers[GAIA] == "MILITIA" and GAIA not in g.enemies and b.enemies[GAIA] == "MILITIA"
    assert f"tag {GAIA} add aoe2mc.p1" in g.sent and f"team join p1 {GAIA}" in g.sent
    assert f"aoe stop {GAIA}" in g.sent and any("A Militia joins you." in c for c in plain_log(g.sent))
    assert savegame.owner_record(g)["units"][GAIA] == 1


def test_a_far_unit_stays_gaia_and_animals_keep_their_rule():
    g, _, _, objects = game(gaia_at=(40.0, 40.0))
    gaia.tick(g)
    assert objects[0]["player"] == 0 and not g.sent
    animals = [{"kind": "unit", "name": n, "player": 0, "uuid": u, "tile": [10.0, 10.0]}
               for n, u in (("SHEEP", SHEEP), ("DEER", DEER))]
    g, _, _, objects = game(objects=animals)
    gaia.tick(g)
    assert all(o["player"] == 0 for o in objects) and not g.sent


def test_an_unconvertible_unit_stays_gaia():
    g, _, _, objects = game(unconvertible=True)
    gaia.tick(g)
    assert objects[0]["player"] == 0


def test_a_unit_of_a_bot_takes_it_for_the_bot():
    g, b, pos, objects = game()
    pos[VILL], pos[MILITIA] = (200.0, 70.0, 0.0), (10 * T + T, 70.0, 10 * T)
    gaia.tick(g)
    assert objects[0]["player"] == 2 and b.soldiers[GAIA] == "MILITIA" and g.enemies[GAIA] == "MILITIA"


def test_no_join_on_vanilla_and_once_per_look():
    g, _, _, objects = game()
    g.paper = False
    gaia.tick(g)
    assert objects[0]["player"] == 0
    g.paper, g.gaia = True, {"at": 0.0}
    gaia.tick(g)
    assert objects[0]["player"] == 0                                 # the next look comes after EVERY seconds
