"""A person who joins a game of two people, or changes the side, gets the fog hides of its own team only (#3070).
The plugin hid the units of all team hides on the join (no team yet): `aoe hide <name> team` (run.Game.side, choose)
shows the units that the fog of another team hides."""
import shutil
import time

import pytest

from game import run


def test_side_and_choose_send_the_team_fog_on_paper_only():
    g = run.Game.__new__(run.Game)
    g.people, g.sides, g.kind, sent = 2, {}, "vanilla", []
    g.command = sent.append
    g.side("Alex")
    assert sent == ["team join p1 Alex"]                                         # vanilla has no plugin
    g.kind = "paper"
    g.side("Steve")
    assert sent[-2:] == ["team join p2 Steve", "aoe hide Steve team"]
    assert g.choose("Alex", 2) is False
    g.sides.pop("Steve")
    assert g.choose("Alex", 2)
    assert sent[-2:] == ["team join p2 Alex", "aoe hide Alex team"]


@pytest.mark.mc
def test_a_person_who_joins_sees_the_own_units_that_the_other_fog_hides(tiny_world, tmp_path):
    import mc_shot
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import")) or not mojang_reachable() or not paper_reachable():
        pytest.skip("Xvfb, Mojang or Paper is not available")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        game.people, game.sides = 2, {}
        for c in ("team add p1", "team add p2"):
            game.command(c)
        a, b = "00000000-0000-0000-0000-000000000bfe", "00000000-0000-0000-0000-000000000bff"   # 3070, 3071
        for i, u in ((3070, a), (3071, b)):
            game.command(f'summon zombie 6 80 {i - 3068} {{UUID:[I;0,0,0,{i}],NoAI:1b,NoGravity:1b}}')
        game.command(f"aoe hide @a[team=p2] {a}")                    # the fog of player 2 hides a unit of player 1
        game.command(f"aoe hide @a[team=p1] {b}")
        with mc_shot.Client(game.game_port, game.version) as client:
            client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
            time.sleep(2)
            game.side("aoe2mc")
            time.sleep(3)
            assert game.command(f"aoe sees aoe2mc {a}").strip() == "Sees: 1"
            assert game.command(f"aoe sees aoe2mc {b}").strip() == "Sees: 0"
