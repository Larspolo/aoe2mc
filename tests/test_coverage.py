"""tools/coverage.py writes a report with a summary and one table per group."""
import coverage as cov


def test_coverage_report(tmp_path):
    out = tmp_path / "coverage.md"
    cov.main(["coverage.py", str(out)])
    text = out.read_text()
    for title in ("## Buildings", "## Other objects", "## Units", "## Heroes"):
        assert title in text
    assert "| KREPOST | krepost | no |" in text
    assert "| MILITIA | zombie – default infantry | no |" in text
    assert "| generic | yes |" in text       # some buildings still use the fallback design
