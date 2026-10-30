"""game/techtree.py: the chat command /trigger aoe_techtree opens the tech tree of the own civilization (#3670).
A person with a score of 1 gets the menu, and a person without a score gets none. Fake server."""
from test_flare import Server
from test_gather import grid

from game import gather, techtree


def setup():
    server = Server({"Steve": {"Pos": (5.5, 65.0, 9.5), "Rotation": (0.0, 60.0)}})
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)], [])
                      | {"players": {"0": {}, "1": {}, "2": {}}}).setup()
    g.clock, g.who = (lambda: server.t), "@a"
    server.t = 0.0
    return server, g


def test_the_trigger_opens_the_tech_tree_and_resets_the_score():
    server, g = setup()
    assert f"scoreboard objectives add {techtree.OBJECTIVE} trigger" in server.log
    server.scores[techtree.OBJECTIVE] = 1                              # /trigger aoe_techtree
    techtree.tick(g)
    assert server.scores[techtree.OBJECTIVE] == 0                      # used once
    assert any(c.startswith("aoe menu-add Steve Tech%20tree ") for c in server.log)


def test_a_person_without_a_score_gets_no_menu():
    server, g = setup()
    techtree.tick(g)
    assert not any("Tech%20tree" in c for c in server.log)
    assert f"scoreboard players enable @a {techtree.OBJECTIVE}" in server.log
