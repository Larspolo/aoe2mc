"""game/wonder.py with a bot (#1220): the wonder of a bot counts, and a game with a bot does not stop with an error."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
from test_cheat_end import game  # noqa: E402
from test_wonder import SITE, targets, tick  # noqa: E402

from game import bot, combat  # noqa: E402


def test_the_complete_wonder_of_a_bot_starts_its_timer():
    server, g = game()
    b = bot.Bot(server, g.data, player=2, share=g).setup()
    g.bots = [b]
    site = {**SITE, "player": 2}
    x0, x1, z0, z1 = site["footprint"]
    targets(server, {combat.target_uuid([x0, z0, x1, z1])})
    b.g.sites.append(site)                                     # the sites of a bot are in its own Gather
    tick(g, 0)
    assert [t["player"] for t in g.wonders.values()] == [2]
    assert "bossbar set aoe2mc:wonder_p2 players @a" in server.log
