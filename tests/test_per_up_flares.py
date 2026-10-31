"""The flare commands of an AI script (#4971): up-send-flare puts a flare at the point, up-find-flare and
up-find-player-flare read the newest live flare into a goal pair. The map of test_bot_gather (player 1 a person, the
bot is player 2)."""
from test_bot_gather import bot_map

from game import per
from game.bot import build, train  # noqa: F401  the modules that per uses


def script(body, facts="(true)"):
    server, me, b = bot_map()
    me.bots = [b]                                                  # run.py: player 1 holds the bots
    s = per.Script(per.parse(f"(defconst gl-point-x 100)(defconst gl-point-y 101)\n(defrule {facts} => {body})"), b)
    return s, b, me


def test_send_flare_puts_one_flare_at_the_point():
    s, b, me = script("(up-send-flare gl-point-x)")
    T = b.g.data["tile_size"]
    s.goals[100], s.goals[101] = 5, 6                              # tile (5, 6)
    s.step()
    assert len(b.g.flares) == 1
    x, y, z, until = b.g.flares[0]
    assert (x, z) == (5 * T, 6 * T) and y == b.g.map.y(x, z) and until > b.g.clock()
    assert not s.warned


def test_find_flare_reads_the_newest_ally_flare_into_the_goal():
    s, b, me = script("(up-find-flare gl-point-x)")
    T = b.g.data["tile_size"]
    now = b.g.clock()
    b.g.flares = [(40, 64, 8, now + 5), (12 * T, 64, 3 * T, now + 9), (0, 64, 0, now - 1)]
    s.step()
    assert (s.goals[100], s.goals[101]) == (12, 3)                 # the newest live flare; the expired one is no choice
    s.goals[100], s.goals[101] = 7, 7
    b.g.flares = []
    s.step()
    assert (s.goals[100], s.goals[101]) == (7, 7)                  # no flare: the goal pair keeps its tiles


def test_find_player_flare_reads_the_flare_of_that_player():
    s, b, me = script("(up-find-player-flare 1 gl-point-x)")
    T = b.g.data["tile_size"]
    now = me.clock()
    me.flares = [(2 * T, 64, 9 * T, now + 5)]                      # the person (player 1) put a flare
    b.g.flares = [(30, 64, 30, now + 9)]                           # a flare of the bot is not the player's
    s.step()
    assert (s.goals[100], s.goals[101]) == (2, 9)
    assert not s.warned
