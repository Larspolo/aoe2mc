"""A complete unit whose building cannot put it out stays at the head of the queue and comes out later (#2470)."""
from test_train_castle import setup

from game import train


def test_a_complete_unit_waits_in_the_queue_until_it_can_come_out(monkeypatch):
    server, g = setup()
    rect = train.open_menu(g, "Steve", (12, 4))
    assert train.queue(g, "Steve", (12, 4), "LONGBOWMAN")
    real, pop = train.spawn, g.pop
    monkeypatch.setattr(train, "spawn", lambda g, rect, name: None)    # no free cell in front of the castle
    assert train.tick(g, 2 * train.TRAIN_TIMES["LONGBOWMAN"]) == [] and train.tick(g, 5) == []
    assert [q["name"] for q in g.queues[rect]] == ["LONGBOWMAN"] and g.queues[rect][0]["progress"] == 1
    assert g.pop == pop
    monkeypatch.setattr(train, "spawn", real)
    assert len(train.tick(g, 0.1)) == 1 and not g.queues[rect] and g.pop == pop + 1
    assert train.tick(g, 1) == []                                      # it comes out once
