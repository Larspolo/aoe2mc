"""pacer.yml reads the secrets of the accounts one by one, not as `toJSON(secrets)`: GitHub held runs that read all
secrets as "may be malicious" (2026-10-30). The present secrets of one account work as before."""
import json
import os
import re

import pytest

import pacer
from test_pacer_accounts import secrets, server, usage_of  # noqa: F401 (server is a fixture)

ONE = {"accounts": {"lars": {}}, "pacing": {"weights": {"haiku": 0.25, "deep": 4.0}}}
TWO = {"accounts": {"lars": {}, "bob": {}}, "pacing": ONE["pacing"]}


def github(values, config):
    """The env of the pacer step as GitHub gives it: the names of `secret_names`, and "" for each slot whose secret
    does not exist (or for an empty name)."""
    names = pacer.secret_names(config)
    return {"SECRET_NAMES": json.dumps(names), **{f"SECRET_{i}": values.get(n, "") for i, n in enumerate(names)}}


def test_one_account_reads_the_present_secret_names():
    names = pacer.secret_names(ONE)
    assert len(names) == pacer.SLOTS
    assert [n for n in names if n] == ["CLAUDE_CODE_OAUTH_TOKEN", "PACER_URL_MAIN", "PACER_TOKEN_MAIN",
                                       "PACER_URL_HAIKU", "PACER_TOKEN_HAIKU", "PACER_URL_DEEP", "PACER_TOKEN_DEEP"]
    found = pacer.accounts(github(secrets("u"), ONE), config=ONE)
    assert [name for name, _ in found] == ["lars"]
    assert pacer.has_url(found[0][1], "main") and not pacer.has_url(found[0][1], "deep")


def test_each_table_of_accounts_adds_the_secrets_with_its_name():
    names = pacer.secret_names(TWO)
    assert {"CLAUDE_CODE_OAUTH_TOKEN_BOB", "PACER_URL_BOB_MAIN", "PACER_TOKEN_BOB_DEEP"} <= set(names)
    found = pacer.accounts(github(secrets("u"), TWO), config=TWO)
    assert [name for name, _ in found] == ["lars", "bob"]
    assert found[1][1] == {"CLAUDE_CODE_OAUTH_TOKEN": "t2", "PACER_URL_MAIN": "u/bob", "PACER_TOKEN_MAIN": "m2"}


def test_too_many_accounts_for_the_slots_is_an_error():
    many = {"accounts": {f"a{i}": {} for i in range(pacer.SLOTS)}, "pacing": ONE["pacing"]}
    with pytest.raises(ValueError, match="SLOTS"):
        pacer.secret_names(many)


def test_the_workflow_has_one_line_per_slot_and_no_dump_of_all_secrets():
    path = os.path.join(os.path.dirname(__file__), "..", ".github", "workflows", "pacer.yml")
    text = open(path).read()
    slots = re.findall(r"SECRET_(\d+): \$\{\{ secrets\[fromJSON\(needs\.names\.outputs\.list\)\[(\d+)\]\] \}\}", text)
    assert slots == [(str(i), str(i)) for i in range(pacer.SLOTS)]
    assert "{{ toJSON(secrets) }}" not in text and "pacer.py --secrets" in text


def test_a_single_account_starts_its_runs_with_the_present_secrets(monkeypatch, server):  # noqa: F811
    url, got = server
    monkeypatch.setattr(pacer.usage, "read_usage", lambda timeout=120, token=None: usage_of(0.1))
    monkeypatch.setattr(pacer.usage, "read_status", lambda: ([], ""))
    monkeypatch.setattr(pacer.usage, "fire", lambda found, now, *a, **kw: (2, {}, "x"))
    first = {k: v for k, v in secrets(url).items() if "BOB" not in k}
    with pytest.raises(SystemExit) as e:
        pacer.main([], env=github(first, ONE))
    assert e.value.code == 0 and got == [("/first", "Bearer m1")] * 2
