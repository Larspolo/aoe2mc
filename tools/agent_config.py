"""The project values of the agent system from `agent.toml` at the root (#905).

`AGENT_CONFIG` names another file (the tests use a fake config). The tools read `CONFIG` once at import."""
import os
import subprocess
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(path=None):
    with open(path or os.environ.get("AGENT_CONFIG") or os.path.join(ROOT, "agent.toml"), "rb") as f:
        return tomllib.load(f)



def account():
    """The Claude account of this run (#4236): `git config aoe2mc.account` (the SessionStart hook copies the variable
    AGENT_ACCOUNT of the cloud environment), else None: then the lines get no account word."""
    r = subprocess.run(["git", "config", "--get", "aoe2mc.account"], capture_output=True, text=True)
    return r.stdout.strip() or None


def first_account(config=None):
    """The name of the first table of `[accounts]`: a line with no account word belongs to it. None with no table."""
    return next(iter((CONFIG if config is None else config).get("accounts", {})), None)


CONFIG = load()
