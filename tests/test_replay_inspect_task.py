"""Live replay: the info line of a unit shows its task, attack, armor and range (inspect(), #5287). Fake RCON."""
import json

import lang
import pytest
from test_replay_inspect import combat, facing, setup


def line(r):
    (c,) = [c for c in r.inspect(10000, clock=lambda: 0.0) if " actionbar " in c]
    return "".join(lang.plain(p) for p in json.loads(c.split(" actionbar ", 1)[1]))


@pytest.mark.parametrize("state, word", [
    (lambda r: r.builds.update({7: (1, None)}), "building"),
    (lambda r: r.working.update({7: 1}), "gathering"),
    (lambda r: r.follows.update({7: [8, "follow", None, None]}), "following"),
    (lambda r: r.follows.update({7: [8, "guard", None, None]}), "guarding"),
    (lambda r: r.patrols.update({7: [[], 1, 1]}), "patrolling"),
    (lambda r: r.moving.update({7: 1}), "walking"),
    (lambda r: r.garrisons.update({(1, 1): [7]}), "garrisoned"),
    (lambda r: None, "idle"),
])
def test_each_state_gives_its_task_and_the_stats(state, word):
    r = setup()
    facing(r, 40.0)
    state(r)
    s = combat.stats("ARCHER")
    text = line(r)
    task, stats = text.split(" | ")[1:]
    assert task.split()[0] == word
    assert stats.startswith(f"{s.attack} atk {s.melee}/{s.pierce} arm")
    assert len(text.split(" | ", 1)[1]) <= 60
