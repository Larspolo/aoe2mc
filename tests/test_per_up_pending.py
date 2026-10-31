"""The queue and research facts of AI scripts: up-pending-objects, up-pending-placement, up-research-status,
up-train-site-ready (#4870)."""
from test_per_bot import scripted

from game import per
from game.bot import build

FACTS = """(defrule (true) => (research ri-loom) (train villager) (build house) (disable-self))
(defrule (up-pending-objects c: villager == 1) => (set-goal 1 1))
(defrule (up-pending-objects c: house == 1) => (set-goal 2 1))
(defrule (up-research-status c: ri-loom == research-pending) => (set-goal 3 1))
(defrule (up-train-site-ready c: villager) => (set-goal 4 1))
(defrule (up-pending-placement c: house) => (set-goal 5 1))"""


def stepped(text, steps=2):
    b = scripted(text)
    b.g.techs.update(build.AGE_TECHS[:1])
    b.g.stock.update(food=1000, wood=1000, gold=1000, stone=1000)
    for _ in range(steps):
        b.script.step()
    return b


def test_the_facts_on_a_queue_a_site_and_a_research():
    b = stepped(FACTS)
    assert {k for k, v in b.script.goals.items() if v == 1} == {1, 2, 3, 4}   # a site was free: no pending placement


def test_up_pending_placement_while_no_site_is_free(monkeypatch):
    monkeypatch.setattr(build, "near", lambda *a: None)
    b = stepped(FACTS)
    assert b.script.goals.get(5) == 1 and 2 not in b.script.goals


def test_the_five_research_states():
    b = stepped("(defrule (true) => (research ri-loom) (research ri-wheel-barrow) (disable-self))", 1)
    s, g = b.script, b.g

    def state(tech):
        return next(v for k, v in per.RESEARCH_STATE.items() if s.check(("up-research-status", "c:", tech, "==", k)))

    assert state("ri-loom") == per.RESEARCH_STATE["research-pending"]
    assert state("ri-wheel-barrow") == per.RESEARCH_STATE["research-queued"]
    assert state("ri-town-watch") == per.RESEARCH_STATE["research-available"]
    assert state("ri-chemistry") == per.RESEARCH_STATE["research-unavailable"]
    g.techs.add(s.game("ri-loom", "tech"))
    assert state("ri-loom") == per.RESEARCH_STATE["research-complete"]
