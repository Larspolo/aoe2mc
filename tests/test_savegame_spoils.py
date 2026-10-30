"""A saved game keeps the plugin scores that already gave gold (#2513, epic #2253): the world keeps the scores of the
mounted kills and the attack gold, so a load must not give their gold again. Fake server of test_gather."""
import json

from test_kill_spoils import game

from game import savegame, spoils, train


def scored(server, kills, ticks):
    """A fake score; spoils.attacks removes the hits that gave gold (#4464). Return the scores."""
    command, scores = server.command, {spoils.OBJECTIVE: kills, spoils.GOLD: ticks}

    def answer(c):
        for o, n in scores.items():
            if c == f"scoreboard players get p1 {o}":
                return f"p1 has {n} [{o}]"
            if c.startswith(f"scoreboard players remove p1 {o} "):
                scores[o] -= int(c.split()[-1])
                return ""
        return command(c)
    server.command = answer
    return scores


def played(civ):
    server, g = game(civ)
    train.summon(g, "VARANGIAN_GUARD", (8.5, 64.0, 8.5))               # spoils.attacks reads the score only with one
    g.stock["gold"] = 0
    g.scores = scored(server, 5, 400000)                       # gold per 100 minutes × ticks (#4464)
    spoils.kills(g)
    spoils.attacks(g)
    return g


def loaded(g, civ):
    server, h = game(civ)
    train.summon(h, "VARANGIAN_GUARD", (8.5, 64.0, 8.5))
    scored(server, *g.scores.values())                                 # the saved world has the same scores
    savegame.load(h, json.loads(json.dumps(savegame.dump(g), sort_keys=True)))
    return h


def test_a_loaded_game_gives_no_second_gold_for_the_old_kills_and_hits():
    for civ in ("MAPUCHE", "VARANGIANS"):
        g = played(civ)
        assert g.stock["gold"] > 0
        h = loaded(g, civ)
        saved = {k: vars(g)[k] for k in savegame.SPOILS if k in vars(g)}   # Mapuche: kills, Varangians: hits
        assert {k: vars(h)[k] for k in saved} == saved
        gold = h.stock["gold"]
        spoils.kills(h)
        spoils.attacks(h)
        assert h.stock["gold"] == gold == g.stock["gold"]


def test_a_save_before_the_spoils_loads():
    server, g = game("BRITONS")
    d = json.loads(json.dumps(savegame.dump(g), sort_keys=True))
    assert not set(savegame.SPOILS) & set(d["players"]["1"])
    _, h = game("BRITONS")
    savegame.load(h, d)
    assert not set(savegame.SPOILS) & set(vars(h))
