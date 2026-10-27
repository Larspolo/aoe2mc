"""`health.api_pages` reads all pages of the comments of the period (#1717: the 20-page cap cut the last hours)."""
import health


def pages(n, size=100):
    calls = []

    def api(path):
        calls.append(path)
        page = int(path.rsplit("page=", 1)[1])
        return [{"n": page}] * (size if page < n else 51)
    return api, calls


def test_fetch_reads_more_than_twenty_pages_of_comments(monkeypatch):
    api, calls = pages(23)
    monkeypatch.setattr(health, "api", api)
    out = health.api_pages("issues/comments?since=x", limit=health.COMMENT_PAGES)
    assert len(calls) == 23 and len(out) == 22 * 100 + 51


def test_a_cut_at_the_limit_warns(monkeypatch, capsys):
    api, _ = pages(30)
    monkeypatch.setattr(health, "api", api)
    assert len(health.api_pages("issues/comments?since=x", limit=3)) == 300
    assert "stopped at 3 pages" in capsys.readouterr().err


def test_a_stop_does_not_warn(monkeypatch, capsys):
    api, _ = pages(30)
    monkeypatch.setattr(health, "api", api)
    health.api_pages("issues/events?", limit=2, stop=lambda e: True)
    assert capsys.readouterr().err == ""
