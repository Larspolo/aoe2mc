"""The AoE2 lobby setting "Reveal map: Explored" (#2932): `game/run.py --reveal explored` starts the minimap of each
player with all tiles explored (dim, not black), and the enemy units out of sight stay hidden as with "normal"."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import combat  # noqa: E402
import fog  # noqa: E402
import gather  # noqa: E402
import run  # noqa: E402

E1 = "00000000-0000-0000-0000-00000000000e"


def side(reveal, size=4):
    return types.SimpleNamespace(player=1, reveal=reveal, map=types.SimpleNamespace(T=4), data={"map_size": size})


def test_explored_starts_with_all_tiles_dim_and_the_sight_seen():
    out = fog.minimap(side("explored"), {"tiles": {(1, 1)}})
    assert out[:2] == ["aoe minimap fog 4 4 p1", "aoe minimap see p1 1,1,1"]
    dim = {(x, y) for c in out if c.startswith("aoe minimap dim") for y, x0, x1 in
           (map(int, r.split(",")) for r in c.split()[4:]) for x in range(x0, x1 + 1)}
    assert dim == {(x, y) for x in range(4) for y in range(4)} - {(1, 1)}


def test_normal_starts_with_no_explored_tile():
    assert fog.minimap(side("normal"), {"tiles": {(1, 1)}}) == ["aoe minimap fog 4 4 p1", "aoe minimap see p1 1,1,1"]


def test_explored_hides_an_enemy_out_of_sight_as_normal():
    g = gather.Gather.__new__(gather.Gather)
    g.player, g.data, g.map, g.paper, g.reveal = 1, {"objects": []}, types.SimpleNamespace(T=4), True, "explored"
    g.villagers, g.soldiers, g.sites, g.enemies = {"v": None}, {}, [], {E1: "MILITIA"}
    g.players, g.bots, g.sent = {}, [], []
    g.command = g.sent.append
    far = 10 + combat.sight("VILLAGER") + 3
    assert fog.update(g, {"v": (42.0, 70.0, 42.0), E1: ((far + 0.5) * 4, 70.0, 42.0)}) == [f"aoe hide @a[team=p1] {E1}"]


def test_the_help_names_the_three_options(capsys):
    try:
        run.main(["--help"])
    except SystemExit:
        pass
    text = " ".join(capsys.readouterr().out.split())
    assert "{normal,explored,all}" in text
