"""The fog of war of team p2 in a game of two people (#1631): the Gather of player 2 hides the units of player 1."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import combat  # noqa: E402
import fog  # noqa: E402
import gather  # noqa: E402
import run  # noqa: E402

T = 4
V1, V2 = "00000000-0000-0000-0000-0000000000a1", "00000000-0000-0000-0000-0000000000a2"
NEW = "00000000-0000-0000-0000-0000000000b1"       # a unit that player 1 trained: not in aoe2mc.json


def bare(player, villagers, enemies):
    g = gather.Gather.__new__(gather.Gather)
    g.player, g.data, g.map, g.paper = player, {"objects": []}, types.SimpleNamespace(T=T), True
    g.villagers, g.soldiers, g.sites, g.enemies = dict.fromkeys(villagers), {}, [], enemies
    g.players, g.bots, g.sent, g.now = {}, [], [], 0.0
    g.command, g.clock = g.sent.append, lambda: g.now
    return g


def game():
    """Two Gathers as run.play joins them: g1 steps the Side of g2, g2 sees g1 through peers."""
    g1, g2 = bare(1, (V1,), {V2: "VILLAGER"}), bare(2, (V2,), {V1: "VILLAGER"})
    g1.bots = [run.Side(g2)]
    g2.peers = [g1]
    return g1, g2


def at(x, y):
    return (x + 0.5) * T, 70.0, (y + 0.5) * T


def test_units_of_player_1_out_of_sight_hide_for_team_p2():
    g1, g2 = game()
    g1.soldiers = {NEW: "MILITIA"}
    far = 10 + combat.sight("VILLAGER") + 3
    pos = {V2: at(10, 10), V1: at(far, 10), NEW: at(10, far)}
    assert fog.update(g2, pos) == [f"aoe hide @a[team=p2] {V1} {NEW}"]
    assert fog.update(g1, {V1: at(10, 10), V2: at(11, 10)}) == []   # in the sight of player 1


def test_a_unit_in_sight_of_player_2_does_not_hide():
    g1, g2 = game()
    g1.soldiers = {NEW: "MILITIA"}
    assert fog.update(g2, {V2: at(10, 10), V1: at(11, 10), NEW: at(10, 11)}) == []


def test_the_side_ticks_the_fog_and_reveal_all_turns_it_off():
    g1, g2 = game()
    g2.point = g2.step = lambda: None
    g2.clicks = lambda: []
    g2.where = lambda want: {V2: at(10, 10), V1: at(60, 10)}
    g1.bots[0].step()
    assert g2.sent == [f"aoe hide @a[team=p2] {V1}"]
    g2.sent.clear()
    g2.reveal, g2.fog["hidden"], g2.now = "all", set(), 5.0
    g1.bots[0].step()
    assert g2.sent == []


def test_gathers_lists_each_gather_once():
    g1, g2 = game()
    g2.peers = [g1, g2]
    assert fog.gathers(g2) == [g2, g1]
    assert fog.gathers(g1) == [g1, g2]
