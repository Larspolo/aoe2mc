"""health.fetch() reads the issue events of the whole period, not only 5 pages (#2005)."""
import datetime

import health
import metrics_log

NOW = datetime.datetime.now(datetime.timezone.utc)


def fake(monkeypatch, per_hour=300):
    """A GitHub fake: `issues/events?` newest first, `per_hour` events an hour for 3 days; the rest is empty."""
    events = [{"created_at": f"{NOW - datetime.timedelta(seconds=3600 * i / per_hour):%Y-%m-%dT%H:%M:%SZ}"}
              for i in range(72 * per_hour)]
    pages = []

    def api(path):
        if path.startswith("issues/events?"):
            page = int(path.rsplit("page=", 1)[1])
            pages.append(page)
            return events[(page - 1) * 100:page * 100]
        if path.startswith("actions/runs?"):
            return {"workflow_runs": []}
        return []
    monkeypatch.setattr(health, "api", api)
    monkeypatch.setattr(metrics_log, "api", api)                 # the status comments (#1983)
    monkeypatch.setattr(metrics_log, "load", lambda since: None)
    return pages


def test_the_events_are_read_past_5_pages_to_the_start_of_the_period(monkeypatch):
    pages = fake(monkeypatch)
    events = health.fetch(NOW - datetime.timedelta(hours=24))[-1]
    assert max(pages) > 5
    assert events[-1]["created_at"] < f"{NOW - datetime.timedelta(hours=24):%Y-%m-%dT%H:%M:%SZ}"


def test_a_48_hour_period_gets_twice_the_page_limit():
    assert health.event_pages(NOW - datetime.timedelta(hours=48), NOW) == 2 * health.event_pages(
        NOW - datetime.timedelta(hours=24), NOW)
