"""game/flare.py: the allies of a player see and hear its flare too (#1942): one command per allied team. Fake server."""
from test_flare import Server
from test_gather import grid
from test_lang_orders import component, plain_json

from game import flare, gather

FLARE = ("playsound", "particle", "tellraw")


def setup(players):
    server = Server({"Steve": {"Pos": (5.5, 65.0, 9.5), "Rotation": (0.0, 60.0)}})
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)], []) | {"players": players}, start={}).setup()
    g.clock = lambda: server.t
    server.t = 0.0
    return server, g


def sent(server, kind, team):
    return [c for c in server.log if c.startswith(kind) and f"@a[team={team}]" in c]


def test_a_flare_of_p1_reaches_its_ally_p3_and_not_the_enemy_p2():
    server, g = setup({"0": {}, "1": {"team": 1}, "2": {"team": 2}, "3": {"team": 1}})
    assert flare.teams(g) == ["@a[team=p1]", "@a[team=p3]"]
    flare.put(g, "Steve", 5, 65, 9)
    for kind in FLARE:
        assert len(sent(server, kind, "p1")) == len(sent(server, kind, "p3")) == 1
        assert not sent(server, kind, "p2")
    assert all("Steve: Flare at 5 9" in plain_json(component(c)) for c in sent(server, "tellraw", "p3"))
    server.t = 5.0
    flare.tick(g)                                                      # the column stays for each allied team
    assert len(sent(server, "particle", "p1")) == len(sent(server, "particle", "p3")) == 2
    assert not sent(server, "particle", "p2")


def test_without_allies_the_flare_reaches_only_the_own_team():
    for players in ({"0": {}, "1": {}, "2": {}, "3": {}}, {"0": {}, "1": {"team": 1}, "2": {"team": 2}}):
        server, g = setup(players)
        assert flare.teams(g) == ["@a[team=p1]"]
        flare.put(g, "Steve", 5, 65, 9)
        assert [c for c in server.log if c.startswith(FLARE)] == flare.commands("Steve", 5, 65, 9, "@a[team=p1]")
