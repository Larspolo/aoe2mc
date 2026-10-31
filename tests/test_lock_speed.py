"""The AoE2 lobby setting "Lock Speed" (#2933, epic #2263): with `run.py --unlock-speed` the button "Game speed" of
the Game menu changes the speed of the whole game (the server tick rate and the steps of the Gathers, as --speed),
and the chat tells all players. Without the option (AoE2 default: locked) the Game menu has no such button."""
from test_gather import FakeServer, grid

from game import diplomacy, gather, menu, recap


def setup(unlock):
    server = FakeServer({})
    g = gather.Gather(server, grid([[64] * 8 for _ in range(8)], [])).setup()
    g.unlock_speed = unlock
    return server, g


def click(server, g, slot):
    diplomacy.open_menu(g, "Steve")
    server.scores[menu.OBJECTIVE] = slot + 1
    g.clicks()


def test_a_click_on_game_speed_makes_the_game_faster_for_all():
    server, g = setup(True)
    diplomacy.open_menu(g, "Steve")
    assert f"{diplomacy.SPEED_SLOT}:clock:Game%20speed:" in server.log[-1]
    click(server, g, diplomacy.SPEED_SLOT)
    assert g.speed == 1.5 and "tick rate 30" in server.log
    assert any(c.startswith("tellraw @a") and '"translate": "aoe2mc.diplomacy.speed"' in c and '"1.5"]' in c for c in server.log)
    assert "aoe menu-close Steve" in server.log
    click(server, g, diplomacy.SPEED_SLOT)
    click(server, g, diplomacy.SPEED_SLOT)                             # after the fastest speed: Normal again
    assert g.speed == 1.0 and server.log.count("tick rate 20") == 1


def test_the_game_time_does_not_jump_at_a_speed_change():
    server, g = setup(True)
    now = [100.0]
    g.clock, g.t0 = lambda: now[0], 40.0
    before = recap.game_time(g)
    diplomacy.faster(g)
    assert g.speed == 1.5 and abs(recap.game_time(g) - before) < 1e-9


def test_without_the_option_the_speed_is_locked():
    server, g = setup(False)
    diplomacy.open_menu(g, "Steve")
    assert ":Game%20speed:" not in server.log[-1]
    click(server, g, diplomacy.SPEED_SLOT)
    assert g.speed == 1.0 and not any(c.startswith("tick rate") for c in server.log)
