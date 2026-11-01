"""After a takeover of player 1 a bot plays each other player of the record from its replay state (#5452)."""
import json

import gather
import savegame
import takeover
from test_gather import FakeServer
from test_takeover_state import played

from game import bot


def loaded(t=750):
    """The Gather of player 1 and the bot of player 2 after a load of the takeover state at game time t (ms)."""
    r, d = played()
    state = json.loads(json.dumps(takeover.state(r, t)))
    server = FakeServer({u: {"Pos": (o["tile"][0] * 4, 70.0, o["tile"][1] * 4)} for o in d["objects"]
                         if (u := o.get("uuid"))})
    me = gather.Gather(server, json.loads(json.dumps(d)), start={}).setup()
    me.bots = [bot.Bot(server, me.data, player=2, share=me, foe=1, start={}).setup()]
    savegame.load(me, state)
    savegame.bots_again(me, state)
    return r, state, me, me.bots[0]


def test_the_bot_of_player_2_has_the_replay_state_and_no_new_town():
    r, state, me, b = loaded()
    assert "bot" not in state["players"]["1"] and state["players"]["2"]["bot"]["foe"] == 1
    two = state["players"]["2"]
    assert b.g.stock == two["stock"] == {k: max(0, int(v)) for k, v in r.resources(2).items()}
    assert sorted(b.g.techs) == two["techs"] and b.g.pop == two["pop"]
    assert [u["uuid"] for u in b.g.units] == ["u2"] and set(b.g.villagers) == {"u2"}
    assert b.g.sites == [] and [s["name"] for s in me.sites] == ["HOUSE"]   # no start town of its own


def test_the_bot_attacks_two_minutes_after_the_takeover():
    _, _, _, b = loaded(t=600_000)
    assert b.time == 600 and not b.charged and b.attack == 600 + takeover.ATTACK
    clock = b.time
    while clock < b.attack:                                            # a fake clock: the bot time of each tick
        assert clock - 600 < 120
        clock += 1
    assert clock - 600 == 120
