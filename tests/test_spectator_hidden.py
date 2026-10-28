"""A spectator (team spec, #2898) sees the units that the fog hides for the teams of the players (#2921, epic #2897).
The plugin keeps the team of each `aoe hide @a[team=T]`: a player who joins later gets only the hides of its team (a
player with no team yet gets all, as the replay view), and `aoe show <name> all` (run.Game.side) shows the units of
the team hides to a new spectator. The minimap reads the hides of the team of each player, not one global set."""
import shutil
import time

import pytest

from game import run


def test_a_spectator_gets_the_fog_units_shown_on_paper_only():
    g = run.Game.__new__(run.Game)
    g.people, g.sides, g.kind, sent = 2, {"Alex": 1, "Steve": 2}, "vanilla", []
    g.command = sent.append
    g.side("Bob")
    assert "aoe show Bob all" not in sent and "team join spec Bob" in sent       # vanilla has no plugin
    g.kind = "paper"
    g.side("Eve")
    assert sent[-1] == "aoe show Eve all"


@pytest.mark.mc
def test_a_spectator_sees_a_unit_and_its_dot_that_the_fog_hides_for_a_team(tiny_world, tmp_path):
    import mc_shot
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import")) or not mojang_reachable() or not paper_reachable():
        pytest.skip("Xvfb, Mojang or Paper is not available")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        game.command("item replace entity aoe2mc weapon.mainhand with minecraft:filled_map[minecraft:map_id=0]")
        for c in ("team add p1", "team add p2", "team modify p2 color blue", *run.SPECTATORS, "team join p1 aoe2mc"):
            game.command(c)
        assert "Minimap: on" in game.command("aoe minimap on")
        time.sleep(3)
        empty = game.command("aoe minimap tile 6 2").split()[3]
        uuid = "00000000-0000-0000-0000-000000000b69"                         # 2921 = 0xb69
        game.command('summon zombie 6 80 2 {UUID:[I;0,0,0,2921],NoAI:1b,NoGravity:1b,Tags:["u"]}')
        game.command("team join p2 @e[tag=u]")
        assert game.command(f"aoe hide @a[team=p1] {uuid}").strip() == "Hidden: 1 entities, 1 players"
        assert game.command(f"aoe hide @a[team=p2] {uuid}").strip() == "Hidden: 1 entities, 0 players"
        time.sleep(3)
        assert game.command(f"aoe sees aoe2mc {uuid}").strip() == "Sees: 0"     # a player of p1: hidden
        assert game.command("aoe minimap tile 6 2").split()[3] == empty           # and no dot
        game.command("team join spec aoe2mc")
        assert game.command("aoe show aoe2mc all").strip() == "Shown: 1 entities, 1 players"
        time.sleep(3)
        assert game.command(f"aoe sees aoe2mc {uuid}").strip() == "Sees: 1"     # the spectator sees it
        assert game.command("aoe minimap tile 6 2").split()[3] != empty           # and its dot
