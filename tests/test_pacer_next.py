"""The `next:` line of a pacer brief (#5076): up to 2 free tickets beyond the runs of the cycle, related ones first. The
pacer does not claim them: the run claims one itself after its PR."""
import claim
import dashboard
import pacer
import ticket_context


def issue(n, body=""):
    return {"number": n, "title": f"T{n}", "body": body, "labels": [{"name": "P2"}]}


def briefs(monkeypatch, tickets, plan):
    """Briefs of one cycle with the runs `plan` (tasks) and the queue `tickets`; claims always win, no network."""
    got = []
    monkeypatch.setattr(pacer, "red_main", lambda: False)
    monkeypatch.setattr(pacer, "queues", lambda open_all, refs, now, tasks: {t: list(tickets) for t in tasks})
    monkeypatch.setattr(pacer, "stuck", lambda *a, **kw: [])
    monkeypatch.setattr(dashboard, "pages", lambda path, limit=10: [])
    monkeypatch.setattr(claim, "claim", lambda n, **kw: got.append(n) or True)
    monkeypatch.setattr(ticket_context, "context", lambda body: "")
    found = {"five_hour": (0.2, 0, "allowed")}
    return pacer.Briefs([(t, "u", "t") for t in plan], {"open": []}, 0, found), got


def head(text):
    return dict(x.split(": ", 1) for x in text.split("\n\n")[0].split("\n")[1:])


def test_the_next_line_has_the_related_tickets_first(monkeypatch):
    queue = [issue(1, "Change `pacer.py`."), issue(2, "Other `x.py`."), issue(3, "Part of #9"), issue(4, "Also `pacer.py`.")]
    b, claimed = briefs(monkeypatch, queue, ["main"])
    n, _, text, after = b.take("main")
    assert n == 1 and after == [4, 2] and head(text)["next"] == "4 2"
    assert claimed == [1]                                              # the pacer claims only the ticket of the run
    lines = text.split("\n")
    assert lines[lines.index("next: 4 2") - 1].startswith("context: ")


def test_two_briefs_of_one_cycle_get_other_tickets(monkeypatch):
    b, claimed = briefs(monkeypatch, [issue(k) for k in range(1, 9)], ["main", "main"])
    first, second = b.take("main"), b.take("main")
    assert (first[0], second[0]) == (1, 2)                             # the next run keeps its ticket
    numbers = [first[0], second[0], *first[3], *second[3]]
    assert len(set(numbers)) == len(numbers) == 6 and claimed == [1, 2]


def test_no_next_line_when_the_runs_take_all_tickets(monkeypatch):
    b, claimed = briefs(monkeypatch, [issue(1), issue(2), issue(3)], ["main"] * 3)
    texts = [b.take("main") for _ in range(3)]
    assert [t[0] for t in texts] == [1, 2, 3] and all(t[3] == [] and "\nnext:" not in t[2] for t in texts)


def test_a_next_ticket_goes_to_an_extra_run_only_when_no_other_is_free(monkeypatch):
    b, _ = briefs(monkeypatch, [issue(1), issue(2), issue(3)], ["main"])
    assert b.take("main")[3] == [2, 3]
    assert b.take("main")[0] == 2                                      # a run beyond the plan still gets a brief
