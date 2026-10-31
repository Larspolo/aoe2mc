"""game/relic_victory.py: a player whose own monasteries hold all relics for the relic timer wins (#1263)."""
from test_relics import setup

from game import relic_victory, wonder

HOME = (14, 18, 2, 6)


def start():
    server, g = setup()
    server.log.clear()                                                 # the bars of the setup
    return server, g


def total(g):
    return wonder.years(g.data.get("map_size")) * wonder.YEAR


def test_all_relics_in_an_own_monastery_win_after_the_timer():
    server, g = setup()
    g.relics[0].update(at=None, home=HOME)
    relic_victory.tick(g, 0)
    assert f"bossbar set {relic_victory.BAR} players @a" in server.log
    assert f'bossbar set {relic_victory.BAR} name "Player 1: relics, {wonder.years(g.data.get("map_size"))} years left"' in server.log
    relic_victory.tick(g, total(g) - 3)
    assert not g.ended
    assert f'bossbar set {relic_victory.BAR} name "Player 1: relics, 1 year left"' in server.log
    relic_victory.tick(g, 3)
    assert g.ended == "Victory" and 'title @a[team=p1] title {"translate":"aoe2mc.victory","fallback":"Victory","color":"gold"}' in server.log
    assert f"bossbar remove {relic_victory.BAR}" in server.log


def test_a_relic_outside_a_monastery_starts_no_timer():
    server, g = start()
    relic_victory.tick(g, 10000)
    assert not g.ended and not any(c.startswith("bossbar") for c in server.log)


def test_no_relic_on_the_map_no_relic_victory():
    server, g = start()
    g.relics.clear()
    relic_victory.tick(g, 10000)
    assert not g.ended and not any(c.startswith("bossbar") for c in server.log)


def test_a_relic_that_leaves_stops_the_timer():
    server, g = setup()
    g.relics[0].update(at=None, home=HOME)
    relic_victory.tick(g, total(g) - 10)
    g.relics[0].update(at=(16, 7), home=None)                          # the monastery fell: the relic lies at its door
    relic_victory.tick(g, 5)
    assert f"bossbar remove {relic_victory.BAR}" in server.log
    assert 'tellraw @a {"text": "Player 1 lost a relic.", "color": "red"}' in server.log
    g.relics[0].update(at=None, home=HOME)
    relic_victory.tick(g, 10)                                          # a new start: the full time again
    assert not g.ended


def test_a_fallen_monastery_counts_at_once():
    server, g = setup()
    g.relics[0].update(at=None, home=(0, 1, 0, 1))                    # not a monastery of the player
    relic_victory.tick(g, 10000)
    assert not g.ended


def test_the_relics_of_a_rival_end_the_game_with_defeat():
    server, g = setup()
    rival = type("Bot", (), {})()
    rival.g = type("G", (), {"player": 2, "relics": [{"at": None, "monk": None, "home": HOME}]})()
    g.bots = [rival]
    monk = relic_victory.monk                                          # the bare module that relic_victory imports
    monasteries = monk.monasteries
    monk.monasteries = lambda b: {HOME} if b is rival.g else monasteries(b)
    try:
        relic_victory.tick(g, 0)
        relic_victory.tick(g, total(g))
    finally:
        monk.monasteries = monasteries
    assert g.ended == "Defeat" and 'title @a[team=p1] title {"translate":"aoe2mc.defeat","fallback":"Defeat","color":"red"}' in server.log
