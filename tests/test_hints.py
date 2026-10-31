"""game/hints.py: the action bar shows the actions of the selection state (#798, owner decision #797)."""
import json

import pytest
from test_select_type import setup

from game import hints, lang


def plain_state(st):
    return st[0], lang.plain(st[1])


def game():
    server, g = setup()
    now = [100.0]
    g.clock = lambda: now[0]
    return server, g, now


def bar(server):
    return {c.split()[1]: lang.plain(json.loads(c.split(" actionbar ", 1)[1])) for c in server.log if " actionbar " in c}


def test_each_state_has_its_hint():
    _, g, _ = game()
    assert hints.state(g)[0] == "none"
    g.select("v-1")
    assert plain_state(hints.state(g)) == ("villagers", "1 villager · Right click: gather, build, build menu · Empty box: deselect")
    g.select("m-1")
    assert hints.state(g)[0] == "military" and lang.plain(hints.state(g)[1]).startswith("1 military unit ·")
    g.corners["Steve"] = (2, 8)
    assert hints.state(g, "Steve")[0] == "corner" and hints.state(g)[0] == "military"
    del g.corners["Steve"]
    g.ghosts = {"Steve": ["LUMBER_CAMP", "green"]}
    assert lang.plain(hints.state(g, "Steve")[1]).startswith("Place the Lumber Camp: right click")


def test_the_hint_changes_at_once_and_repeats_while_the_state_lasts():
    server, g, now = game()
    hints.tick(g)
    assert bar(server) == {"@a": lang.plain(hints.hint("none-wand"))}
    server.log.clear()
    now[0] += 5
    hints.tick(g)
    assert not bar(server)                                             # the idle hint shows once
    g.select("m-1")
    hints.tick(g)
    assert bar(server)["@a"].startswith("1 military unit ·")            # at once, without a wait
    server.log.clear()
    now[0] += 0.5
    hints.tick(g)
    assert not bar(server)
    now[0] += hints.REPEAT
    hints.tick(g)
    assert bar(server)["@a"].startswith("1 military unit ·")            # again before the action bar fades


def test_a_player_with_a_corner_gets_an_own_hint():
    server, g, _ = game()
    g.select("v-1")
    hints.tick(g)
    server.log.clear()
    g.box("Steve", (2, 8))
    hints.tick(g)
    shown = bar(server)
    assert shown["Steve"] == lang.plain(hints.hint("corner"))
    assert shown["@a[name=!Steve]"] == "1 villager · Right click: gather, build, build menu · Empty box: deselect"   # the other players
    g.box("Steve", (10, 18))
    server.log.clear()
    hints.tick(g)
    assert bar(server) == {"@a": "4 military units · Right click: attack an enemy, stance menu · Empty box: deselect"}


def test_clicks_send_the_hint():
    server, g, _ = game()
    g.clicks()
    assert bar(server) == {"@a": lang.plain(hints.hint("none-wand"))}


@pytest.mark.mc
def test_the_hint_commands_work_on_a_server(tiny_world, tmp_path):
    import shutil

    from game import gather, run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    data = json.load(open(world / "aoe2mc.json"))
    with run.Game(world) as game:
        game.forceload()
        g = gather.Gather(game, data).setup()
        sent = []
        command = game.command
        game.command = lambda c: sent.append((c, command(c))) or sent[-1][1]
        v, = g.villagers.values()
        g.select(v.uuid)
        g.corners["Steve"] = (0, 0)
        hints.tick(g)
        assert len([c for c, _ in sent if " actionbar " in c]) == 2
        bad = [(c, out) for c, out in sent if any(w in out for w in ("Unknown", "Incorrect", "Invalid", "Expected", "Failed to parse"))]
        assert not bad, bad
