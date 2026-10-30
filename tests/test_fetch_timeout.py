"""The git calls of framework/tools/health.py and framework/tools/metrics_log.py end in a fixed time (#3290)."""
import datetime
import subprocess

import health
import metrics_log


def hang(*args, **kwargs):
    raise subprocess.TimeoutExpired(args[0], kwargs.get("timeout"))


def test_claim_refs_reads_a_hung_fetch_as_none(monkeypatch):
    monkeypatch.setattr(health.subprocess, "run", hang)
    assert health.claim_refs() is None


def test_metrics_load_reads_a_hung_fetch_as_none(monkeypatch):
    monkeypatch.setattr(metrics_log.subprocess, "run", hang)
    since = datetime.datetime(2026, 10, 28, tzinfo=datetime.timezone.utc)
    assert metrics_log.load(since) is None
