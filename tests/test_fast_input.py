"""game/gather.py: the game program reads the input of the players each INPUT seconds, also between the game steps
(#5760). The plugin sets the score aoe_input; Gather.choose sends the glow and the tag of many units in few commands."""
from test_deselect import paper
from test_gather_clock import fake_clock, loop

from game import gather


def waiting(monkeypatch, clicks_at=()):
    """A Paper Gather on a fake clock. A click comes at each time of clicks_at. Returns g, the clock, the handled
    (time, name) pairs and the input checks."""
    server, g = paper()
    mono, _, _ = fake_clock(monkeypatch)
    due, handled, checks = sorted(clicks_at), [], []
    sleep = gather.time.sleep

    def tick(s):
        sleep(s)
        while due and due[0] <= mono[0]:
            due.pop(0)
            server.scores[gather.INPUT_SCORE] = 1
    monkeypatch.setattr(gather.time, "sleep", tick)
    command = g.command

    def watch(c):
        if gather.INPUT_SCORE in c and c.startswith("execute"):
            checks.append(mono[0])
        if c.startswith("scoreboard players reset") and gather.INPUT_SCORE in c:
            server.scores.pop(gather.INPUT_SCORE, None)
            return ""
        return command(c)
    monkeypatch.setattr(g, "command", watch)
    monkeypatch.setattr(g, "inputs", lambda: ["Steve"])
    monkeypatch.setattr(g, "click", lambda name: handled.append((mono[0], name)))
    return g, mono, handled, checks


def test_a_click_in_the_wait_is_handled_within_input_seconds(monkeypatch):
    g, mono, handled, _ = waiting(monkeypatch, [0.01])
    g.wait_input(0.25)
    assert len(handled) == 1 and handled[0][0] - 0.01 <= gather.INPUT + 1e-9
    assert mono[0] == 0.25


def test_no_click_sends_one_check_each_input_seconds_and_returns_at_the_deadline(monkeypatch):
    g, mono, handled, checks = waiting(monkeypatch)
    g.wait_input(0.25)
    assert handled == [] and mono[0] == 0.25
    assert len(checks) <= round(0.25 / gather.INPUT)
    assert all(b - a >= gather.INPUT - 1e-9 for a, b in zip(checks, checks[1:]))


def test_the_steps_keep_their_time_with_no_input(monkeypatch):
    mono, _, _ = fake_clock(monkeypatch)
    g = loop(monkeypatch, lambda n: None)
    g.paper, g.who = False, "@a"                                       # vanilla: the check of aoe_use
    g.command = lambda c: ""                                           # no input
    n = []
    g.step = lambda: n.append(mono[0])
    g.run(until=lambda: len(n) >= 5)
    assert [round(t, 6) for t in n] == [0.0, 0.25, 0.5, 0.75, 1.0]


def test_choose_of_40_units_sends_at_most_5_commands_on_paper(monkeypatch):
    server, g = paper()
    monkeypatch.setattr(gather.bossbar, "show", lambda g, u: None)
    units = {f"u-{i}" for i in range(40)}
    server.log.clear()
    g.choose(units)
    assert g.selected == units
    selects = [c for c in server.log if c.startswith("aoe select")]
    assert len(server.log) <= 5 and selects
    assert {u for c in selects for u in c.split()[4:]} == units and all(c.split()[3] == gather.SELECT for c in selects)
