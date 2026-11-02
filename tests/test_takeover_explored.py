"""The explored tiles of each player of a live replay are in its take-over save (#5602): the minimap of the take-over
shows them, not a black map."""
import json

import gather
import savegame
import takeover
from test_gather import FakeServer
from test_takeover_state import played


def inside(r, p):
    n = r.data.get("map_size") or r.n // r.T
    return {(x, y) for x, y in r.explored.get(p, ()) if 0 <= x < n and 0 <= y < n}


def test_the_state_has_the_explored_tiles_of_the_player():
    r, _ = played()
    r.explore()
    state = takeover.state(r, 750)
    tiles = {(x, y) for y, x0, x1 in state["players"]["1"]["explored"] for x in range(x0, x1 + 1)}
    assert r.explored[1] and tiles == inside(r, 1)


def test_a_load_gives_the_explored_tiles_to_the_minimap():
    r, d = played()
    r.explore()
    text = json.dumps(takeover.state(r, 750), sort_keys=True)
    server = FakeServer({u: {"Pos": (o["tile"][0] * 4, 70.0, o["tile"][1] * 4)} for o in d["objects"]
                         if (u := o.get("uuid"))})
    g = gather.Gather(server, json.loads(json.dumps(d)), start={}).setup()
    savegame.load(g, json.loads(text))
    assert g.fog["explored"] == inside(r, 1)
