"""The production panel of the live replay ends an age-up at the "age" event of the record (#3739): player 1 of the
sample reaches the Feudal Age at 10:42.2, the queue guess ended it 24 s later."""
from test_replay_production_record import make


def ages(r, t):
    return [item for item in r.production(t).get(1, []) if item[0] == "Feudal Age"]


def test_the_feudal_age_ends_at_the_age_event():
    r = make()
    at = next(e["time"] for e in r.data["timeline"] if e["kind"] == "age" and e.get("player") == 1
              and e.get("age") == "FEUDAL_AGE")
    (item,) = ages(r, at - 10000)
    assert item[2] == at and item[3] == "age" and item[1] <= at - 10000
    assert ages(r, at + 1000) == []
