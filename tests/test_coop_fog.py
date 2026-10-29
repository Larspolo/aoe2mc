"""The fog of war and the minimap in a co-op game (#3671, epic #3485): two people on player 1 (--seats 1,1) share the
fog and the minimap of player 1. The team selector @a[team=p1] and the minimap team p1 reach both of them."""
import os
import re
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import fog  # noqa: E402
import gather  # noqa: E402

T = 4
V1, V2 = "00000000-0000-0000-0000-0000000000a1", "00000000-0000-0000-0000-0000000000a2"
PEOPLE = {"Alex": 1, "Steve": 1, "Ann": 2}                 # Alex and Steve are co-op partners on player 1


def bare(player, villagers, enemies):
    g = gather.Gather.__new__(gather.Gather)
    g.player, g.data, g.map, g.paper = player, {"objects": [], "map_size": 16}, types.SimpleNamespace(T=T), True
    g.villagers, g.soldiers, g.sites, g.enemies = dict.fromkeys(villagers), {}, [], enemies
    g.players, g.bots, g.sent, g.now = {}, [], [], 0.0
    g.command, g.clock = g.sent.append, lambda: g.now
    return g


def at(x, y):
    return (x + 0.5) * T, 70.0, (y + 0.5) * T


def reached(cmd):
    """The names of the people that the command reaches: the team of its selector (@a[team=pN]) or of its team name
    (`aoe minimap ... pN`)."""
    team = re.search(r"\bp(\d)\b", cmd).group(1)
    return sorted(name for name, p in PEOPLE.items() if p == int(team))


def test_the_fog_commands_of_player_1_reach_both_partners():
    g = bare(1, (V1,), {V2: "VILLAGER"})
    cmds = fog.update(g, {V1: at(10, 10), V2: at(60, 10)})
    assert cmds == [f"aoe hide @a[team=p1] {V2}"]
    assert [reached(c) for c in cmds] == [["Alex", "Steve"]]


def test_the_minimap_fog_of_player_1_reaches_both_partners():
    g = bare(1, (V1,), {V2: "VILLAGER"})
    fog.update(g, {V1: at(10, 10), V2: at(60, 10)})
    cmds = fog.minimap(g, g.fog)
    assert cmds[0] == "aoe minimap fog 4 16 p1"
    assert cmds and all(reached(c) == ["Alex", "Steve"] for c in cmds)


def test_a_reveal_of_player_1_reaches_both_partners_and_not_ann():
    g = bare(1, (V1,), {V2: "VILLAGER"})
    fog.update(g, {V1: at(10, 10), V2: at(60, 10)})
    g.sent.clear()
    fog.reveal(g)
    assert g.sent == [f"aoe show @a[team=p1] {V2}"]
    assert reached(g.sent[0]) == ["Alex", "Steve"]
    assert "Ann" not in reached(g.sent[0])


def test_the_commands_of_player_2_do_not_reach_the_partners():
    g = bare(2, (V2,), {V1: "VILLAGER"})
    cmds = fog.update(g, {V2: at(10, 10), V1: at(60, 10)})
    assert cmds == [f"aoe hide @a[team=p2] {V1}"]
    assert reached(cmds[0]) == ["Ann"]
