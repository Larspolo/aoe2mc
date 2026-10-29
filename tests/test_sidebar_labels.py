"""The sidebar line of the population limit reads "Pop. limit" (owner, #990)."""
from test_train_population import setup, train, train_all


def test_the_limit_line_reads_pop_limit_once():
    server, g = setup()
    assert 'scoreboard players display name Limit aoe_res "Pop. limit"' in server.log
    g.sites.append({"name": "HOUSE", "player": 1, "footprint": [0, 2, 20, 22], "progress": 1.0, "done": True})
    train_all(g, server, train.CENSUS)
    assert f"scoreboard players set Limit aoe_res {train.limit(g)}" in server.log
    assert sum("display name Limit" in c for c in server.log) == 1          # only when the line appears
