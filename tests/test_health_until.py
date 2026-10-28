"""tools/health.py --until: the numbers of a period in the past, to compare a period before and after a change (#489)."""
import datetime

import health

UNTIL = datetime.datetime(2026, 10, 26, 5, 0, tzinfo=datetime.timezone.utc)
URL = "https://api.github.com/repos/Larspolo/aoe2mc/issues/"


def test_clip_drops_the_items_after_the_end():
    runs = [{"created_at": "2026-10-26T04:59:00Z"}, {"created_at": "2026-10-26T05:00:00Z"}]
    comments = [{"issue_url": URL + "7", "created_at": "2026-10-26T04:00:00Z",
                 "body": "CI is green, but the merge failed (not mergeable)."},
                {"issue_url": URL + "8", "created_at": "2026-10-26T06:00:00Z",
                 "body": "CI is green, but the merge failed (not mergeable)."}]
    prs = [{"closed_at": "2026-10-26T04:00:00Z", "merged_at": "2026-10-26T04:00:00Z"},
           {"closed_at": "2026-10-26T06:00:00Z", "merged_at": "2026-10-26T06:00:00Z"},
           {"closed_at": None, "merged_at": None}]
    r, s, c, p, i, e = health.clip(UNTIL, runs, comments, comments, prs, [], [])
    assert r == runs[:1] and s == c == comments[:1] and p == prs[:1] and i == e == []
    assert health.conflicted(c) == [7]


def test_until_sets_the_period_of_the_fetch(monkeypatch):
    seen = {}

    def fetch(since, until):
        seen.update(since=since, until=until)
        return [], [], [], [], [], [], []
    monkeypatch.setattr(health, "fetch", fetch)
    monkeypatch.setattr(health, "git_files", lambda: [])
    monkeypatch.setattr(health, "claim_refs", lambda remote="origin": None)
    monkeypatch.setattr("feedback.fetch", lambda: [])
    assert health.main(["--hours", "24", "--until", "2026-10-26T05:00:00Z"]) == 0
    assert seen == {"since": UNTIL - datetime.timedelta(hours=24), "until": UNTIL}
