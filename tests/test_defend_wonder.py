"""#2441: `run.py --play --mode defend-the-wonder` is the AoE2 DE game mode "Defend the Wonder" (wiki "Defend the
Wonder"): player 1 starts with a Wonder; the attackers win when it falls, the defenders when it stands for the years of
the mode.
Fake server of test_gather, the town map of test_empire_wars."""
from test_empire_wars import town_map

from game import defend_wonder, gather, run, wonder

MODE = defend_wonder.MODE


def game(teams=None):
    g = town_map()
    g.players = g.data["players"] = {"1": {"color": "blue", "team": teams and teams[0]},
                                     "2": {"color": "red", "team": teams and teams[1]}}
    g.mode = "defend-the-wonder"
    return defend_wonder.setup(g)


def test_the_defender_starts_with_a_complete_wonder_for_free():
    g = game()
    site = next(s for s in g.sites if s["name"] == "WONDER")
    assert site.get("done") and g.defender == 1 and g.wonder
    assert {r: g.stock[r] for r in MODE["sides"]["defender"]} == MODE["sides"]["defender"]
    assert g.wonder in wonder.found(g)                                 # the wonder victory counts it


def test_the_attackers_win_when_the_wonder_falls():
    g = game()
    g.wonders_gone = {g.wonder}                                        # wonder.tick: its target is gone
    defend_wonder.tick(g)
    assert g.ended == "Defeat"                                         # player 1 defends: it loses


def test_the_defenders_win_when_the_wonder_stands_for_the_years_of_the_mode():
    g, years = game(), MODE["wonder_years"]
    g.command = lambda c: "Test passed" if c.startswith("execute if entity") else ""   # the target stands
    wonder.tick(g, 0)
    assert g.wonders[g.wonder]["left"] == years * wonder.YEAR          # not the timer of the map size
    wonder.tick(g, years * wonder.YEAR)
    assert g.ended == "Victory"
    defend_wonder.tick(g)                                              # the game ended: no second end
    assert g.ended == "Victory"


def test_the_side_of_each_player():
    g = game(teams=(1, 1))                                             # player 2 is a team mate of the defender
    assert defend_wonder.side(g, 1) == "defender" and defend_wonder.side(g, 2) == "ally"
    assert defend_wonder.side(game(teams=(1, 2)), 2) == "attacker"


def test_the_mode_is_a_choice_of_run_py():
    assert "defend-the-wonder" in run.MODES and gather.Gather.mode == "standard"
