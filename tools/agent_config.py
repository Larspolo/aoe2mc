"""The project values of the agent system from `agent.toml` at the root (#905), and the owner's settings of the system
(`[pacing]`, `[review]`) from `steering/system/system.toml` (#4194).

`AGENT_CONFIG` names another first file (the tests use a fake config); then the second file is `AGENT_SYSTEM`, or none.
The tools read `CONFIG` once at import."""
import os
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


SYSTEM = os.path.join(ROOT, "steering", "system", "system.toml")


def load(path=None, system=None):
    """The dict of the first file, joined with the sections of the second file when it exists (a section in both:
    ValueError)."""
    with open(path or os.environ.get("AGENT_CONFIG") or os.path.join(ROOT, "agent.toml"), "rb") as f:
        config = tomllib.load(f)
    system = system or os.environ.get("AGENT_SYSTEM") or (None if path or os.environ.get("AGENT_CONFIG") else SYSTEM)
    if system and os.path.exists(system):
        with open(system, "rb") as f:
            extra = tomllib.load(f)
        if both := sorted(set(config) & set(extra)):
            raise ValueError(f"{system} and the project file both have {both}")
        config.update(extra)
    return config


CONFIG = load()
