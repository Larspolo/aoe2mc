"""tools/coverage.py writes a report with a summary and one table per group. The fallbacks must not go up."""
import pytest

import coverage as cov

# Allowed maximums (ratchet). When a count goes down, lower its maximum here in the same PR.
MAX = {"Buildings": {"fallback": 0, "default": 0},
       "Other objects": {"fallback": 41, "default": 0},
       "Units": {"fallback": 16, "default": 74},
       "Heroes": {"fallback": 0, "default": 0}}


@pytest.fixture(scope="module")
def groups():
    return cov.groups()


def test_coverage_report(tmp_path):
    out = tmp_path / "coverage.md"
    cov.main(["coverage.py", str(out)])
    text = out.read_text()
    for title in ("## Buildings", "## Other objects", "## Units", "## Heroes"):
        assert title in text
    assert "| KREPOST | krepost | no |" in text
    assert "| HUSKARL | zombie – default infantry | no |" in text
    assert "| generic | yes |" not in text   # every building has its own design
    assert "| BLOCKER | skipped on purpose (path blocker) | no |" in text
    assert "| HINT_OBJECT | skipped on purpose (editor hint) | no |" in text


@pytest.mark.parametrize("title", MAX)
def test_fallbacks_do_not_go_up(groups, title):
    c = cov.counts(groups)[title]
    for key, limit in MAX[title].items():
        assert c[key] <= limit, f"{title}: {c[key]} {key} > {limit}. See docs/coverage.md (python3 tools/coverage.py)."
        assert c[key] == limit, (f"{title}: {key} went down from {limit} to {c[key]}. Good! Lower MAX['{title}']"
                                 f"['{key}'] in tests/test_coverage.py to {c[key]} and run python3 tools/coverage.py.")
