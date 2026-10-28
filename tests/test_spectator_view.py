"""#2901 (epic #2897): a spectator looks through the eyes of player N with `/trigger aoe_view set N`: the camera follows
the Minecraft player of side N, else the town center of player N (a bot), and the spectator gets the hide commands of
the fog of player N for itself only (`aoe hide NAME view`). The view 0 is the free view: all units show again."""
import os
import re
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import combat  # noqa: E402
import spectator  # noqa: E402
from test_fog_units import E1, E2, at, bare  # noqa: E402

TC = [40, 48, 40, 48]                                                  # x0, x1, z0, z1 of the town center of player 2


def game():
    """Player 1 (the Minecraft player Steve) and the bot player 2, far apart; Alex is a spectator."""
    g, bot = bare(enemies={E2: "MILITIA"}, villagers=(E1,)), bare(player=2, enemies={E1: "MILITIA"}, villagers=(E2,))
    g.reveal, g.bots, g.scores = "normal", [types.SimpleNamespace(g=bot)], {}
    g.game = types.SimpleNamespace(spectators={"Alex"}, sides={"Steve": 1})
    g.data["objects"] = [{"kind": "building", "name": "TOWN_CENTER", "player": 2, "footprint": TC}]
    bot.where = lambda want: {u: p for u, p in {E1: at(10, 10), E2: at(90, 90)}.items() if u in want}
    g.fog = {"hidden": {E2}, "at": 0.0}                                # fog.tick of player 1 ran

    def command(c):
        g.sent.append(c)
        if c.startswith("execute if entity"):
            return "Test passed, count: 1" if any(v >= 0 for v in g.scores.values()) else "Test failed"
        if m := re.fullmatch(r"scoreboard players get (\S+) aoe_view", c):
            return f"{m[1]} has {g.scores[m[1]]} [aoe_view]" if m[1] in g.scores else "Can't get value"
        if m := re.fullmatch(r"scoreboard players set (\S+) aoe_view (-?\d+)", c):
            g.scores[m[1]] = int(m[2])
        return ""
    g.command = command
    return g


def choose(g, n):
    g.scores["Alex"] = n
    del g.sent[:]
    spectator.views(g)
    return g.sent


def test_the_view_of_a_bot_follows_its_town_center_and_hides_what_it_does_not_see():
    g = game()
    sent = choose(g, 2)
    assert f"spectate {combat.target_uuid([40, 40, 48, 48])} Alex" in sent
    assert f"aoe hide Alex view {E1}" in sent                          # the unit of player 1, far from the bot
    assert not [c for c in sent if "team=p" in c] and g.fog["hidden"] == {E2}   # the fog of player 1 stays
    assert g.scores["Alex"] == -1                                      # the choice is read once
    del g.sent[:]
    spectator.views(g)
    assert not [c for c in g.sent if c.startswith(("spectate", "aoe "))]   # only the changes


def test_the_free_view_shows_all_units_again():
    g = game()
    choose(g, 2)
    sent = choose(g, 0)
    assert f"aoe show Alex view {E1}" in sent and "execute as Alex run spectate" in sent
    assert "Alex" not in g.spectator_views


def test_the_view_of_a_person_follows_its_minecraft_player_with_its_fog():
    g = game()
    sent = choose(g, 1)
    assert "spectate Steve Alex" in sent and f"aoe hide Alex view {E2}" in sent
    sent = choose(g, 2)                                                # player 2 sees E2 and not E1
    assert f"aoe hide Alex view {E1}" in sent and f"aoe show Alex view {E2}" in sent


def test_no_spectator_sends_no_command():
    g = game()
    g.game.spectators = frozenset()
    spectator.views(g)
    assert g.sent == []


def test_all_visible_hides_nothing():
    g = game()
    g.reveal = "all"
    sent = choose(g, 2)
    assert not [c for c in sent if c.startswith("aoe hide")] and any(c.startswith("spectate ") for c in sent)
