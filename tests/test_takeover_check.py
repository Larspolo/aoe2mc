"""The pure parts of tools/takeover_check.py (#5702): the trigger value and the points of the result."""
import replay_input
import takeover_check


def one(**kw):
    """A sample of takeover_check.sample()."""
    return {"time": 0.0, "stock": {"food": 200, "gold": 100, "stone": 200, "wood": 100}, "pop": 6, "villagers": 5,
            "idle": 0, "idle_jobs": [], "soldiers": ["SCOUT_CAVALRY"], "queued": 0, "age": [], "bot_sites": {"2": 3}} | kw


SAVED = {"stock": {"food": 200, "gold": 100, "stone": 200, "wood": 90}, "techs": []}


def test_the_trigger_value_takes_over_the_player():
    assert takeover_check.trigger_value(1) == replay_input.TAKEOVER + 1
    assert takeover_check.trigger_value(2) - takeover_check.trigger_value(1) == 1


def test_a_good_game_passes_each_point():
    last = one(stock={"food": 190, "gold": 100, "stone": 200, "wood": 150}, villagers=6, pop=7, bot_sites={"2": 4})
    r = takeover_check.result(SAVED, one(time=310.0), last, queued=1, errors=[], start=300.0)
    assert all(ok for ok, _ in r.values()), r


def test_each_fault_fails_its_point():
    last = one(soldiers=["HAWK", "SCOUT_CAVALRY"], pop=7, stock={"food": 140, "gold": 90, "stone": 200, "wood": 100})
    r = takeover_check.result(SAVED, one(age=["FEUDAL_AGE"]), last, queued=0, errors=["[ERROR] boom"], start=300.0)
    assert {k for k, (ok, _) in r.items() if not ok} == {
        "the clock goes on", "age of the replay", "no Gaia bird joined", "the stock goes up", "food goes up", "the town center trains",
        "a bot builds", "no server errors"}
    assert not takeover_check.result({**SAVED, "stock": {"gold": 50, "stone": 200}}, one(), one(), 0, [])["stock of the replay"][0]
