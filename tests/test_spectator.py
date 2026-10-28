"""A Minecraft player without a side in a game of more people is a spectator (#2898, epic #2897): the game mode
spectator and the team spec, so no Gather reads its clicks. A free side in "Choose your player" makes it play again."""
from game import run


def game(people=2):
    g = run.Game.__new__(run.Game)
    g.people, g.sides, sent = people, {}, []
    g.command = sent.append
    return g, sent


def test_a_player_after_the_sides_is_a_spectator():
    g, sent = game()
    for name in ("Alex", "Steve", "Bob", "Eve"):
        g.side(name)
    assert g.sides == {"Alex": 1, "Steve": 2} and g.spectators == {"Bob", "Eve"}
    assert sent == ["team join p1 Alex", "team join p2 Steve", *run.SPECTATORS, "team join spec Bob",
                    "gamemode spectator Bob", "team join spec Eve", "gamemode spectator Eve"]
    assert not any("gamemode" in c for c in sent[:2])                  # the people keep the creative mode


def test_a_spectator_who_joins_again_is_a_spectator_again():
    g, sent = game()
    for name in ("Alex", "Steve", "Bob"):
        g.side(name)
    sent.clear()
    g.side("Bob")                                                      # force-gamemode made it creative on the join
    assert sent == ["team join spec Bob", "gamemode spectator Bob"]


def test_a_spectator_who_takes_a_free_side_plays_again():
    g, sent = game()
    for name in ("Alex", "Steve", "Bob"):
        g.side(name)
    del g.sides["Steve"]                                               # Steve left its side
    sent.clear()
    assert g.choose("Bob", 2)
    assert sent == ["team join p2 Bob", "gamemode creative Bob"] and "Bob" not in g.spectators
    sent.clear()
    assert g.choose("Alex", 2) is False and not sent                   # a taken side


def test_one_person_has_no_spectators():
    g, sent = game(people=1)
    for name in ("Alex", "Steve"):
        g.side(name)
    assert not sent and not g.spectators                               # all play player 1 (who "@a")


def test_the_gathers_of_the_people_read_only_their_teams():
    import test_two_players as two
    _, g1, g2 = two.setup()
    assert (g1.who, g2.who) == ("@a[team=p1]", "@a[team=p2]")          # never the team spec
