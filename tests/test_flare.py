"""game/flare.py: a flare shows a place to the team (#1234). The players of the team hear a bell, see a column of
end_rod particles for 10 s and read "Flare at X Z" with the name of the player. The button "Flare" of the Game menu
puts it at the look of the player, `/trigger aoe_flare` at the place of the player. Fake server."""
import json
import re

import pytest
from test_gather import FakeServer, grid

from game import diplomacy, flare, gather, menu


class Server(FakeServer):
    """FakeServer with `scoreboard players set` and the score selector of a team."""

    def command(self, cmd):
        if m := re.fullmatch(r"scoreboard players set Steve (\w+) (-?\d+)", cmd):
            self.scores[m[1]] = int(m[2])
        if m := re.fullmatch(r"execute if entity @a\[team=p\d,scores=\{(\w+)=1\.\.\}\]", cmd):
            self.log.append(cmd)
            return "Test passed, count: 1" if self.scores.get(m[1]) else "Test failed"
        if re.fullmatch(r"execute if entity @a\[team=p\d,name=Steve\]", cmd):
            return "Test passed, count: 1"
        return super().command(cmd)


def setup(who="@a", **kw):
    server = Server({"Steve": {"Pos": (5.5, 65.0, 9.5), "Rotation": (0.0, 60.0)}})
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)], [])
                      | {"players": {"0": {}, "1": {}, "2": {}}}, **kw).setup()
    g.clock, g.who = (lambda: server.t), who
    server.t = 0.0
    return server, g


def test_the_commands_reach_only_the_team_of_the_player():
    sound, burst, chat = flare.commands("Steve", 12, 64, 30, "@a[team=p2]")
    assert sound == "playsound minecraft:block.note_block.bell master @a[team=p2] 12 64 30 1 1 1"
    assert burst.startswith("particle minecraft:end_rod 12.5 68 30.5 ") and burst.endswith(" force @a[team=p2]")
    assert chat.startswith("tellraw @a[team=p2] ")
    assert json.loads(chat.split(" ", 2)[2])["text"] == "Steve: Flare at 12 30"


def test_the_trigger_puts_a_flare_at_the_player_and_the_column_lasts_10_seconds():
    server, g = setup()
    assert f"scoreboard objectives add {flare.OBJECTIVE} trigger" in server.log
    g.clicks()
    assert f"scoreboard players enable @a {flare.OBJECTIVE}" in server.log
    assert not any(c.startswith("playsound") for c in server.log)
    server.scores[flare.OBJECTIVE] = 1                                 # /trigger aoe_flare
    g.clicks()
    assert server.scores[flare.OBJECTIVE] == 0                         # used once
    assert "playsound minecraft:block.note_block.bell master @a[team=p1] 5 65 9 1 1 1" in server.log
    assert any(c.startswith("tellraw @a[team=p1] ") and "Steve: Flare at 5 9" in c for c in server.log)
    n = len(server.log)
    server.t = 9.0
    g.clicks()
    assert flare.particles(5, 65, 9, "@a[team=p1]") in server.log[n:]   # the column stays
    n = len(server.log)
    server.t = 10.5
    g.clicks()
    assert not any(c.startswith("particle") for c in server.log[n:])
    assert sum(c.startswith("playsound") for c in server.log) == 1


def test_the_game_menu_button_puts_a_flare_at_the_look_and_closes_the_menu():
    server, g = setup()
    diplomacy.open_menu(g, "Steve")
    assert "1:end_rod:Flare:" in server.log[-1]
    server.scores[menu.OBJECTIVE] = 2                                  # a click on slot 1
    g.clicks()
    assert "aoe menu-close Steve" in server.log
    eye, d = g.look("Steve")
    x, z = g.map.pick_ground(eye, d)
    assert (x, z) != (5, 9)                                            # the look, not the feet
    assert f"playsound minecraft:block.note_block.bell master @a[team=p1] {x} {g.map.y(x, z)} {z} 1 1 1" in server.log


def test_a_second_person_puts_a_flare_for_its_own_team_only():
    server, g = setup(player=2, who="@a[team=p2]")
    server.scores[flare.OBJECTIVE] = 1
    flare.tick(g)
    assert any(c.startswith("playsound") and "@a[team=p2]" in c for c in server.log)
    assert not any("@a[team=p1]" in c for c in server.log if c.startswith(("playsound", "particle", "tellraw")))


@pytest.mark.mc
def test_the_flare_commands_run_on_a_server(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import contextlib
    import io

    import scenarios

    import aoe2mc
    from game import run
    src = str(tmp_path / "flare.aoe2scenario")
    scenarios.save(scenarios.new_scenario(16), src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        g = gather.Gather(game, data).setup()
        g.flares = [(8, 64, 8, g.clock() + flare.SECONDS)]
        out = [game.command(c) for c in flare.commands("Steve", 8, 64, 8, flare.team("p1"))]
        out += [game.command(f"scoreboard players enable @a {flare.OBJECTIVE}")]
        flare.tick(g)
        bad = ("Unknown", "Incorrect", "Expected", "Invalid", "Malformed")
        assert not [o for o in out if any(b in o for b in bad)], out
        # not "scoreboard objectives list": the server cuts its answer after about 150 characters (#2965)
        assert "already exists" in game.command(f"scoreboard objectives add {flare.OBJECTIVE} trigger")
