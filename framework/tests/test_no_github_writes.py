"""The guard of conftest.py: a framework test cannot write to the real repository (#5910)."""
import subprocess
import urllib.request

import conftest
import pytest


@pytest.mark.parametrize("argv", [
    ["gh", "api", "repos/o/n/issues/1/labels", "-X", "POST", "-f", "name=x"],
    ["gh", "api", "repos/o/n/issues/1/comments", "--method", "PATCH"],
    ["gh", "api", "repos/o/n/issues", "-f", "title=x"],
    ["gh", "api", "repos/o/n/issues", "--input", "-"],
    ["gh", "issue", "list"],
    ["gh", "pr", "create"],
])
def test_a_gh_write_fails(argv):
    assert conftest.github_write(argv)
    with pytest.raises(conftest.GitHubWrite):
        subprocess.run(argv, capture_output=True)


@pytest.mark.parametrize("argv", [
    ["gh", "api", "repos/o/n/commits?sha=main", "-X", "GET"],
    ["gh", "api", "repos/o/n/issues?per_page=100&page=1"],
    ["git", "push", "origin", "HEAD"],
])
def test_a_read_is_not_blocked(argv):
    assert not conftest.github_write(argv)


def test_a_github_request_that_writes_fails():
    req = urllib.request.Request("https://api.github.com/repos/o/n/issues/1/comments", data=b"{}")
    assert conftest.github_request(req.full_url, req.get_method())
    with pytest.raises(conftest.GitHubWrite):
        urllib.request.urlopen(req)


def test_a_github_read_and_another_host_are_not_blocked():
    assert not conftest.github_request("https://api.github.com/repos/o/n/issues")
    assert not conftest.github_request("https://example.com/write", "POST")
