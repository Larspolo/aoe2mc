"""The page "Choose your player" of the Game menu in a game of two people (#1563): a click on a free AoE2 player gives
it to the Minecraft player, and its clicks then go to the Gather of that player; a taken side cannot be chosen. Without
a click the join order of #1310 stays."""
import re

import test_two_players as two

from game import diplomacy, lobby, run


class LobbyServer(two.TwoServer):
    """TwoServer with the sides of run.Game: the team of a Minecraft player is its side."""
    people = 2
    choose, side, start_view = run.Game.choose, run.Game.side, run.Game.start_view

    def __init__(self, entities):
        super().__init__(entities)
        self.sides = {}

    def command(self, cmd):
        if m := re.fullmatch(r"execute if entity @a\[team=p(\d),name=(\w+)\]", cmd):
            self.log.append(cmd)
            return "Test passed, count: 1" if self.sides.get(m[2]) == int(m[1]) else "Test failed"
        if m := re.fullmatch(r"execute if entity @a\[team=p(\d),scores=\{(\w+)=1\.\.\}\]", cmd):
            self.log.append(cmd)
            hit = any(self.sides.get(n) == int(m[1]) and o == m[2] for n, o in self.scores)
            return "Test passed, count: 1" if hit else "Test failed"
        return super().command(cmd)


def setup():
    server, g1, g2 = two.setup()
    lob = LobbyServer(server.entities)
    for g in (g1, g2):
        g.game = lob
    return lob, g1, g2


def menu_of(server, player):
    """The last `aoe menu` command of player."""
    return next(c for c in reversed(server.log) if c.startswith(f"aoe menu {player} "))


def test_a_click_on_player_2_gives_it_and_its_clicks_go_to_the_gather_of_player_2():
    server, g1, g2 = setup()
    server.side("Steve")                                               # the join order: player 1
    assert server.sides == {"Steve": 1}
    diplomacy.open_menu(g1, "Steve")
    assert f"{lobby.SLOT}:player_head:Choose%20your%20player" in menu_of(server, "Steve")
    g1.menus["Steve"]("Steve", lobby.SLOT, False)
    page = menu_of(server, "Steve")
    assert "0:" in page and ":You" in page and "1:" in page and ":Free" in page
    g1.menus["Steve"]("Steve", 1, False)                               # Player 2
    assert server.sides == {"Steve": 2} and "team join p2 Steve" in server.log and "Steve" not in g1.menus
    two.click(server, "Steve", "b")
    two.run_clicks(g1, g2)
    assert g2.selected == {"b"} and not g1.selected


def test_a_taken_side_cannot_be_chosen():
    server, g1, g2 = setup()
    server.side("Steve")
    server.side("Alex")
    assert server.sides == {"Steve": 1, "Alex": 2}
    lobby.show(g1, "Steve")
    assert "Taken%20by%20Alex" in menu_of(server, "Steve")
    server.log.clear()
    assert not lobby.choose(g1, "Steve", 2)
    assert server.sides == {"Steve": 1, "Alex": 2} and not any(c.startswith("team join") for c in server.log)
    assert any("is taken" in c for c in server.log)


def test_a_late_player_gets_the_side_that_is_free():
    server, g1, _ = setup()
    server.side("Steve")
    assert lobby.choose(g1, "Steve", 2)
    server.side("Alex")                                                # joins after the choice: player 1 is free
    assert server.sides == {"Steve": 2, "Alex": 1}


def test_one_person_has_no_choose_button():
    server, g1, _ = setup()
    server.people = 1
    diplomacy.open_menu(g1, "Steve")
    assert "Choose" not in menu_of(server, "Steve")
