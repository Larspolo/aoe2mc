"""framework/tools/owner_tasks.py --sample lists the check tickets that the agent closed on its evidence (decision B of #1708)."""
import owner_tasks


def closed(n, title, labels, at, pr=False):
    i = {"number": n, "title": title, "labels": [{"name": x} for x in labels], "state": "closed", "closed_at": at}
    return {**i, "pull_request": {}} if pr else i


def test_sample_lists_the_closed_owner_sample_tickets_the_oldest_first():
    issues = [closed(20, "Check the ships", ("owner-sample", "P3"), "2026-10-27T12:00:00Z"),
              closed(21, "Check the walls", ("owner-sample",), "2026-10-26T09:00:00Z"),
              closed(22, "Check the bot", ("P2",), "2026-10-25T09:00:00Z"),
              closed(23, "A PR", ("owner-sample",), "2026-10-24T09:00:00Z", pr=True)]
    assert [i["number"] for i in owner_tasks.sample(issues)] == [21, 20]


def test_sample_prints_the_batch(monkeypatch, capsys):
    asked = []
    monkeypatch.setattr(owner_tasks, "pages", lambda path: asked.append(path) or
                        [closed(21, "Check the walls", ("owner-sample",), "2026-10-26T09:00:00Z")])
    assert owner_tasks.main(["--sample"]) == 0
    assert asked == ["issues?state=closed&labels=owner-sample"]
    assert capsys.readouterr().out == "#21 Check the walls (closed 2026-10-26)\n"
