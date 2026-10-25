import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "tools")]


def entity_ids(nbt_or_desc):
    """All entity IDs of an entity and its passengers (riders)."""
    out = [str(nbt_or_desc["id"])]
    for p in nbt_or_desc.get("Passengers", []):
        out += entity_ids(p)
    return out


@pytest.fixture(scope="session")
def tiny_world(tmp_path_factory):
    """The synthetic tiny scenario, converted once per test session. Returns (world path, console output)."""
    import contextlib
    import io

    import aoe2mc
    import scenarios

    d = tmp_path_factory.mktemp("tiny")
    src = scenarios.tiny(str(d / "tiny.aoe2scenario"))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        aoe2mc.convert(src, str(d / "TinyWorld"), preview=True)
    return str(d / "TinyWorld"), out.getvalue()
