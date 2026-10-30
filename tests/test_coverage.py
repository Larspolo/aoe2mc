"""tools/coverage.py writes a report with a summary and one table per group. The fallbacks must not go up."""
import coverage as cov
import pytest

# Allowed maximums (ratchet). Do not change them in a PR: the workflow coverage.yml lowers them on main (#233).
MAX = {"Buildings": {"fallback": 0, "default": 0},
       "Other objects": {"fallback": 0, "default": 0},
       "Units": {"fallback": 0, "default": 0},
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
    assert "default infantry |" not in text   # every unit and hero has its own look
    assert "| generic | yes |" not in text   # every building has its own design
    assert "| BLOCKER | skipped on purpose (path blocker) | no |" in text
    assert "| HINT_OBJECT | skipped on purpose (editor hint) | no |" in text


@pytest.mark.parametrize("title", MAX)
def test_fallbacks_do_not_go_up(groups, title):
    c = cov.counts(groups)[title]
    for key, limit in MAX[title].items():
        assert c[key] <= limit, f"{title}: {c[key]} {key} > {limit}. See the report: python3 tools/coverage.py OUT.md"


def test_ratchet_only_lowers(tmp_path):
    src = tmp_path / "t.py"
    src.write_text('MAX = {"Units": {"fallback": 3, "default": 0},\n       "Heroes": {"fallback": 2, "default": 1}}\n')
    c = {"Units": {"fallback": 1, "default": 4}, "Heroes": {"fallback": 2, "default": 0}}
    assert cov.ratchet(c, str(src)) == ["Units fallback: 3 -> 1", "Heroes default: 1 -> 0"]
    assert src.read_text() == ('MAX = {"Units": {"fallback": 1, "default": 0},\n'
                               '       "Heroes": {"fallback": 2, "default": 0}}\n')
