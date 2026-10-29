"""game/gather.py: in a game of two people each team p<n> sees the resources of its own AoE2 player in the sidebar of
its team color (#1309, `scoreboard objectives setdisplay sidebar.team.<color>`). Player 1 keeps the objective aoe_res
and also the sidebar of all; player n gets aoe_res<n>."""
from test_gather import FakeServer, grid

from game import cheats, gather, train

TC1, TC2 = [2, 2, 6, 6], [10, 10, 14, 14]


def two():
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [4.0, 4.0], "footprint": TC1},
               {"kind": "building", "name": "TOWN_CENTER", "player": 2, "tile": [12.0, 12.0], "footprint": TC2}]
    data = grid([[64] * 16 for _ in range(16)], objects)
    data["players"] = {"1": {"civ": "BRITONS", "color": "blue"}, "2": {"civ": "FRANKS", "color": "green"}}
    server = FakeServer({})
    return server, gather.Gather(server, data).setup(), gather.Gather(server, data, player=2).setup()


def test_each_player_shows_its_own_objective_in_the_sidebar_of_its_team_color():
    server, one, two_ = two()
    assert (one.board, two_.board) == ("aoe_res", "aoe_res2")
    log = server.log
    assert "scoreboard objectives setdisplay sidebar aoe_res" in log                   # as before, for all
    assert "team modify p1 color blue" in log and "scoreboard objectives setdisplay sidebar.team.blue aoe_res" in log
    assert "team modify p2 color dark_green" in log                                     # units.TEAM_COLOR
    assert "scoreboard objectives setdisplay sidebar.team.dark_green aoe_res2" in log
    assert 'scoreboard objectives add aoe_res2 dummy "Resources"' in log
    assert "scoreboard objectives setdisplay sidebar aoe_res2" not in log               # not the sidebar of player 1
    assert f"scoreboard players set Wood aoe_res2 {two_.stock['wood']}" in log


def test_the_stock_of_each_player_changes_only_its_own_objective():
    server, one, two_ = two()
    food = train.COSTS["VILLAGER_MALE"]["food"]
    before = len(server.log)
    assert train.queue(two_, "Steve", (11, 11), "VILLAGER_MALE")
    new = server.log[before:]
    assert f"scoreboard players remove Food aoe_res2 {food}" in new and not [c for c in new if " aoe_res " in c + " "]
    before = len(server.log)
    assert train.queue(one, "Steve", (3, 3), "VILLAGER_MALE")
    new = server.log[before:]
    assert f"scoreboard players remove Food aoe_res {food}" in new and not [c for c in new if "aoe_res2" in c]


def test_noui_hides_and_shows_the_team_sidebar_too():
    server, _, two_ = two()
    cheats.noui(two_, "Steve")
    assert server.log[-2] == "scoreboard objectives setdisplay sidebar.team.dark_green"
    cheats.noui(two_, "Steve")
    assert "scoreboard objectives setdisplay sidebar.team.dark_green aoe_res2" in server.log[-2:]
