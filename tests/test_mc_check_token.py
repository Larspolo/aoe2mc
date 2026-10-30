"""mc_check.get sends the workflow token to the GitHub API only (#4629)."""
import sys
import urllib.request

sys.path.insert(0, "tools")
import mc_check  # noqa: E402


class Response:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return b"{}"


def sent(monkeypatch, url, env):
    for k in ("GH_TOKEN", "GITHUB_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    got = []
    monkeypatch.setattr(urllib.request, "urlopen", lambda r, timeout: got.append(r) or Response())
    assert mc_check.get(url) == b"{}"
    r = got[0]
    return r.get_header("Authorization") if isinstance(r, urllib.request.Request) else None


API = "https://api.github.com/repos/adoptium/temurin25-binaries/releases/latest"


def test_api_gets_the_token(monkeypatch):
    assert sent(monkeypatch, API, {"GH_TOKEN": "abc"}) == "Bearer abc"
    assert sent(monkeypatch, API, {"GITHUB_TOKEN": "xyz"}) == "Bearer xyz"


def test_other_host_and_no_token_get_none(monkeypatch):
    assert sent(monkeypatch, "https://piston-data.mojang.com/v1/x.jar", {"GH_TOKEN": "abc"}) is None
    assert sent(monkeypatch, API, {}) is None
