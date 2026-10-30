"""game/wonder.py: a player who keeps a complete wonder for the wonder timer wins (#1137)."""
from test_cheat_end import game

from game import combat, wonder

SITE = {"name": "WONDER", "player": 1, "footprint": (4, 9, 4, 9), "done": True, "progress": 1.0}


def targets(server, alive):
    """Let the fake server answer `execute if entity UUID`: alive holds the UUIDs of the targets that stand."""
    command = server.command

    def answer(cmd):
        if cmd.startswith("execute if entity ") and "@" not in cmd:
            server.log.append(cmd)
            return "Test passed, count: 1" if cmd.split()[-1] in alive else "Test failed"
        return command(cmd)
    server.command = answer


def tick(g, dt):
    g.wonder_at = 0.0                                              # no wait of EVERY seconds
    wonder.tick(g, dt)


def start(site=SITE):
    server, g = game()
    uuid = combat.target_uuid([site["footprint"][0], site["footprint"][2], site["footprint"][1], site["footprint"][3]])
    alive = {uuid}
    targets(server, alive)
    g.sites.append(dict(site))
    server.log.clear()
    tick(g, 0)
    return server, g, uuid, alive


def test_the_timer_depends_on_the_map_size():
    years = [wonder.years(s) for s in (48, 120, 168, 200, 220, 240, 480)]
    assert years == sorted(years) and wonder.years(None) == wonder.years(48)   # a larger map: more years


def test_a_wonder_that_stands_for_the_timer_wins():
    server, g, uuid, _ = start()
    total = wonder.years(g.data.get("map_size")) * wonder.YEAR
    assert any(c.startswith("summon slime ") and "aoe2mc.building" in c for c in server.log)
    s = combat.stats("WONDER")
    assert f"aoe building {uuid} {s.hp} {s.melee} {s.pierce}" in " ".join(server.log)   # a target: units can destroy it
    assert "bossbar set aoe2mc:wonder_p1 players @a" in server.log
    years = wonder.years(g.data.get("map_size"))
    assert f'bossbar set aoe2mc:wonder_p1 name "Player 1: wonder, {years} years left"' in server.log
    tick(g, total - 3)
    assert not g.ended
    assert 'bossbar set aoe2mc:wonder_p1 name "Player 1: wonder, 1 year left"' in server.log
    tick(g, 3)
    assert g.ended == "Victory" and 'title @a[team=p1] title {"text":"Victory","color":"gold"}' in server.log


def test_a_destroyed_wonder_stops_the_timer_and_the_bar_goes():
    server, g, uuid, alive = start()
    tick(g, 100)
    alive.clear()                                                  # the plugin removed the target at 0 hit points
    tick(g, 100)
    assert "bossbar remove aoe2mc:wonder_p1" in server.log
    assert 'tellraw @a {"text": "The wonder of player 1 is destroyed.", "color": "red"}' in server.log
    tick(g, 10000)
    assert not g.ended and not g.wonders


def test_the_wonder_of_a_rival_ends_the_game_with_defeat():
    server, g, uuid, _ = start({**SITE, "player": 2})
    tick(g, wonder.years(None) * wonder.YEAR)
    assert g.ended == "Defeat" and 'title @a[team=p1] title {"text":"Defeat","color":"red"}' in server.log


def test_an_unfinished_wonder_has_no_timer():
    server, g, uuid, _ = start({**SITE, "done": False, "progress": 0.5})
    assert not g.wonders and not any(c.startswith("bossbar") for c in server.log)


def test_the_bar_changes_only_when_the_years_change():
    server, g, uuid, _ = start()
    server.log.clear()
    g.wonder_at = g.clock() + 100                                  # no target check in this tick
    wonder.tick(g, 1)
    assert not server.log
