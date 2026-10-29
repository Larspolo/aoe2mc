"""game/score.py: the AoE2 score of each player, its four parts and its lines in the sidebar (#2355)."""
import types

import pytest

from game import combat, gather, score, train

from test_cheat_end import game

HOUSE = combat.target_uuid([10, 10, 12, 12])
W = score.worth                                                        # the AoE2 cost value of the data


def two_sides():
    """Player 1 (the person) and a bot Gather of player 2, each with 100 food and nothing else in stock."""
    server, g = game()
    g.players = {str(p): {"color": c} for p, c in ((0, "gray"), (1, "blue"), (2, "red"))}
    bot = gather.Gather(server, g.data, player=2)
    g.bots = [types.SimpleNamespace(g=bot)]
    for h in (g, bot):
        h.stock = dict.fromkeys(h.stock, 0) | {"food": 100}
    return server, g, bot


def test_the_points_of_resources_units_technologies_ages_and_a_kill():
    server, g, bot = two_sides()
    train.research(g, {"name": "DOUBLE_BIT_AXE"}, start=True)        # free: a start age technology does not count
    train.research(g, {"name": "LOOM", "player": "Steve"})
    train.research(g, {"name": "FEUDAL_AGE"})
    score.fallen(bot, {"m-2": "MILITIA"})                              # player 1 killed the militia of player 2
    score.razed(g, HOUSE)                                              # and its house
    p = score.points(g)
    assert p[1]["economy"] == pytest.approx(0.1 * 100 + 0.2 * (W("VILLAGER") + W("MILITIA")))   # stock, 2 units
    assert p[1]["technology"] == pytest.approx(0.2 * (W("LOOM") + W("FEUDAL_AGE")))
    assert p[1]["military"] == pytest.approx(0.2 * (W("MILITIA") + W("HOUSE")))
    assert p[1]["society"] == 0
    assert p[2] == {"military": 0, "economy": pytest.approx(10), "technology": 0, "society": 0}   # no militia, no house
    assert score.total(p[1]) == int(sum(p[1].values()))


def test_a_fallen_unit_of_the_census_goes_to_the_rivals():
    server, g, bot = two_sides()
    del server.entities["m-1"]                                         # the militia of player 1 died
    train.census(g)
    assert g.losses == {"m-1": "MILITIA"}
    p = score.points(g)
    assert p[2]["military"] == pytest.approx(0.2 * W("MILITIA"))
    assert p[1]["economy"] == pytest.approx(0.1 * 100 + 0.2 * W("VILLAGER"))


def test_a_castle_that_the_player_built_is_society_not_economy():
    server, g, bot = two_sides()
    g.sites.append({"name": "CASTLE", "player": 1, "footprint": [2, 5, 2, 5], "done": True})
    p = score.points(g)
    assert p[1]["society"] == pytest.approx(0.2 * W("CASTLE"))
    assert p[1]["economy"] == pytest.approx(10 + 0.2 * (W("VILLAGER") + W("MILITIA")))


def tick(g):
    g.score_at = 0.0                                                   # no wait of EVERY seconds
    score.tick(g)


def test_the_sidebar_has_one_line_per_player_and_changes_after_an_event():
    server, g, bot = two_sides()
    g.explore_at = float("inf")                                        # no explored tiles: tests/test_score_explored.py
    server.log.clear()
    tick(g)
    lines = [c for c in server.log if c.startswith("scoreboard players set Score")]
    one, two = (int(10 + 0.2 * (W("VILLAGER") + W("MILITIA"))), int(10 + 0.2 * (W("MILITIA") + W("HOUSE"))))
    assert lines == [f"scoreboard players set Score1 aoe_res {one}", f"scoreboard players set Score2 aoe_res {two}"]
    assert 'scoreboard players display name Score2 aoe_res "Score of player 2"' in server.log
    server.log.clear()
    tick(g)
    assert not [c for c in server.log if c.startswith("scoreboard")]   # no change, no command
    train.research(g, {"name": "LOOM", "player": "Steve"})
    server.log.clear()
    tick(g)
    new = int(10 + 0.2 * (W("VILLAGER") + W("MILITIA") + W("LOOM")))
    assert [c for c in server.log if c.startswith("scoreboard")] == [f"scoreboard players set Score1 aoe_res {new}"]


@pytest.mark.mc
def test_the_score_lines_reach_the_sidebar_on_a_server(tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    import contextlib
    import io
    import json
    import re
    import time

    import aoe2mc
    import scenarios
    from game import run
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(scenarios.four_civs(str(tmp_path / "s.aoe2scenario")), str(tmp_path / "W"))
    data = json.load(open(tmp_path / "W" / "aoe2mc.json"))
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        combat.setup(game, data)
        g = gather.Gather(game, data).setup()
        bot = gather.Gather(game, data, player=2)
        g.bots = [types.SimpleNamespace(g=bot)]
        g.explore_at = bot.explore_at = float("inf")                    # no new explored tiles between the ticks (#2965)

        def shown(n):
            m = re.search(r"has (\d+)", game.command(f"scoreboard players get Score{n} {g.board}"))
            return int(m[1]) if m else None
        tick(g)
        one, two = shown(1), shown(2)
        assert one == score.total(score.points(g)[1]) and two == score.total(score.points(g)[2]) and two > 0
        uuid, name = next(iter(bot.soldiers.items()))                  # a soldier of player 2 dies
        game.command(f"kill {uuid}")
        time.sleep(2)
        train.census(bot)
        tick(g)
        assert abs(shown(1) - one - 0.2 * score.worth(name)) <= 1 and shown(2) < two   # int() of the sums
