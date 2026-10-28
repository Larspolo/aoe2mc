"""#2899 (epic #2897): a spectator (team spec, #2898) sees all units and buildings. The fog of war of the game program
hides the units only for the team of a player (`aoe hide @a[team=pN]`) and sets the minimap fog only for the team of a
player (`aoe minimap fog T N pN`): the team spec gets no hide and no fog, so Minimap.java draws the whole map for it
(no fog of its team, no "known" set: all buildings show). A spectator cannot see the minimap: the game mode spectator
shows no held item, so map 0 shows only in the follow view (#2901)."""
import os
import re
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import fog  # noqa: E402
import run  # noqa: E402
from test_fog_units import E1, E2, at, bare  # noqa: E402


def two_players():
    """Player 1 and its enemy player 2, each with a unit far from the other: each hides the unit of the other."""
    g, foe = bare(enemies={E2: "MILITIA"}, villagers=(E1,)), bare(player=2, enemies={E1: "MILITIA"}, villagers=(E2,))
    for x in (g, foe):
        x.data["map_size"] = 100
    g.bots = [types.SimpleNamespace(g=foe)]
    where = {E1: at(10, 10), E2: at(90, 90)}
    return [c for x in (g, foe) for c in fog.update(x, where) + fog.minimap(x, x.fog)], (g, foe)


def test_the_hide_commands_name_only_the_teams_of_the_players():
    sent, _ = two_players()
    hides = [c for c in sent if c.startswith(("aoe hide", "aoe show"))]
    assert hides == [f"aoe hide @a[team=p1] {E2}", f"aoe hide @a[team=p2] {E1}"]   # each unit is hidden for a team
    assert not any("spec" in c for c in sent)


def test_the_minimap_fog_is_only_for_the_teams_of_the_players():
    sent, _ = two_players()
    teams = {m.group(1) for c in sent if (m := re.match(r"aoe minimap (?:fog \d+ \d+|see|dim|fog off) (\w+)", c))}
    assert teams == {"p1", "p2"} and run.SPECTATORS[0].split()[2] == "spec"


def test_reveal_and_the_shown_units_name_only_the_team_of_the_player():
    _, (g, _) = two_players()
    g.sent.clear()
    fog.reveal(g)                                                      # "polo", Spies
    assert g.sent == [f"aoe show @a[team=p1] {E2}", "aoe minimap fog off p1"]
