"""The project values of the agent system from `agent.toml` at the root (#905).

`AGENT_CONFIG` names another file (the tests use a fake config). The tools read `CONFIG` once at import."""
import os
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(path=None):
    with open(path or os.environ.get("AGENT_CONFIG") or os.path.join(ROOT, "agent.toml"), "rb") as f:
        return tomllib.load(f)


CONFIG = load()
