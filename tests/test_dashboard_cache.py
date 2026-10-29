"""The dashboard site reads only the issues and PRs that changed since its last build (`dashboard_data.cached`,
2026-10-29): all of them were about 60 API pages in each build."""
import datetime as dt

import dashboard_data as dd

T0 = dt.datetime(2026, 10, 29, 18, 0, tzinfo=dt.timezone.utc)


def issue(n, updated, labels=(), body="text", pr=False):
    i = {"number": n, "title": f"T{n}", "state": "open", "created_at": "2026-10-01T00:00:00Z", "closed_at": None,
         "updated_at": updated, "labels": [{"name": x} for x in labels], "body": body, "user": {"login": "x"}}
    return {**i, "pull_request": {"url": "u"}} if pr else i


def pull(n, updated, merged="2026-10-29T17:00:00Z"):
    return {"number": n, "title": f"P{n}", "created_at": "2026-10-29T16:00:00Z", "merged_at": merged,
            "updated_at": updated, "head": {"ref": f"claude/b{n}", "sha": "s"}, "labels": [], "body": "long"}


def test_slim_keeps_the_fields_of_the_data_files_and_only_the_body_of_an_epic():
    assert dd.slim(issue(1, "x"))["body"] == "" and dd.slim(issue(2, "x", ["epic"], "Roadmap: `a:b`"))["body"]
    assert dd.tickets([dd.slim(issue(3, "x", ["P1", "size:S"]))]) == dd.tickets([issue(3, "x", ["P1", "size:S"])])
    assert dd.merged_prs([dd.slim(pull(4, "x"))]) == dd.merged_prs([pull(4, "x")])
    assert "pull_request" in dd.slim(issue(5, "x", pr=True))


def test_the_first_build_reads_all_and_the_next_one_only_the_changes(tmp_path, monkeypatch):
    asked = []

    def read(path):
        asked.append(path)
        if path.startswith("issues?state=all&since="):
            return [issue(1, "2026-10-29T18:05:00Z", ["P0"]), issue(3, "2026-10-29T18:06:00Z")]
        return [issue(1, "2026-10-29T17:00:00Z"), issue(2, "2026-10-29T17:00:00Z")] if path.startswith("issues") \
            else [pull(10, "2026-10-29T17:00:00Z")]
    issues, pulls = dd.cached(tmp_path, T0, read)
    assert asked == ["issues?state=all", "pulls?state=closed"] and len(issues) == 2 and len(pulls) == 1
    pages = {1: [pull(12, "2026-10-29T18:07:00Z")] + [pull(11, "2026-10-29T18:01:00Z")] * 99,
             2: [pull(11, "2026-10-29T18:01:00Z"), pull(9, "2026-10-29T10:00:00Z")]}
    monkeypatch.setattr(dd.health, "api", lambda path: asked.append(path) or pages[int(path.rsplit("page=", 1)[1])])
    issues, pulls = dd.cached(tmp_path, T0 + dt.timedelta(minutes=10), read)
    assert asked[2] == "issues?state=all&since=2026-10-29T17:58:00Z&sort=updated&direction=asc"
    assert len(asked) == 5                                       # the PR pages stop at an update before `since`
    assert {i["number"]: [x["name"] for x in i["labels"]] for i in issues} == {1: ["P0"], 2: [], 3: []}
    assert sorted(p["number"] for p in pulls) == [10, 11, 12]


def test_a_cache_older_than_a_day_reads_all_again(tmp_path):
    asked = []
    read = lambda path: asked.append(path) or []
    dd.cached(tmp_path, T0, read)
    dd.cached(tmp_path, T0 + dt.timedelta(hours=dd.FULL_HOURS + 1), read)
    assert asked == ["issues?state=all", "pulls?state=closed"] * 2
