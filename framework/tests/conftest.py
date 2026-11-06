"""The tests of the generic tools (#4195): they import the tools by name, also the project tools (release.py)."""
import io
import os
import subprocess
import sys
import urllib.request

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [ROOT, os.path.join(ROOT, "framework", "tools"), HERE]
sys.path.append(os.path.join(ROOT, "tools"))


class GitHubWrite(RuntimeError):
    """A test tried to change GitHub: the framework tests never write to the real repository (#5910)."""


BODY_FLAGS = {"-f", "-F", "--field", "--raw-field", "--input"}


def github_write(argv):
    """True when a `gh` call writes: anything but a plain `gh api` read (GET, no request body)."""
    if not argv or argv[0] != "gh":
        return False
    if argv[1:2] != ["api"]:
        return True
    args = argv[2:]
    method = next((args[i + 1] for i, a in enumerate(args[:-1]) if a in ("-X", "--method")), "GET")
    return method.upper() != "GET" or any(a in BODY_FLAGS or a[:2] in ("-f", "-F") for a in args)


def github_request(url, method="GET"):
    """True when a request to api.github.com changes something (any method but GET)."""
    return "api.github.com" in url and method.upper() != "GET"


real_run, real_urlopen = subprocess.run, urllib.request.urlopen


def guarded_run(argv, *args, **kwargs):
    if github_write(list(argv) if isinstance(argv, (list, tuple)) else []):
        raise GitHubWrite(f"a test must not run {' '.join(map(str, argv[:3]))}")
    return real_run(argv, *args, **kwargs)


def guarded_urlopen(req, *args, **kwargs):
    url, method = (req, "GET") if isinstance(req, str) else (req.full_url, req.get_method())
    if github_request(url, method):
        raise GitHubWrite(f"a test must not send {method} {url}")
    return real_urlopen(req, *args, **kwargs)


@pytest.fixture(autouse=True)
def no_github_writes(monkeypatch):
    """No test changes the real repository: each gh call and each request to api.github.com that is not a read fails
    (#5910; a test with a fake of the API patches its own function)."""
    monkeypatch.setattr(subprocess, "run", guarded_run)
    monkeypatch.setattr(urllib.request, "urlopen", guarded_urlopen)


@pytest.fixture(autouse=True)
def empty_stdin(monkeypatch):
    """An empty stdin, as in tests/conftest.py (#2510)."""
    monkeypatch.setattr(sys, "stdin", io.StringIO())


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """The result line also with -qq, as in tests/conftest.py (#2510); only once when both folders run."""
    if config.get_verbosity() < -1 and not getattr(config, "result_line", False):
        config.result_line = True
        counts = {k: len(v) for k, v in terminalreporter.stats.items() if k and k != "warnings"}
        terminalreporter.write_line(", ".join(f"{n} {k}" for k, n in sorted(counts.items())) + f" (exit {exitstatus})")
