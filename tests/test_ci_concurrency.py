"""CI on main: a merge does not cancel the quick run of the merge before it (#2145)."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_main_runs_are_not_cancelled():
    with open(os.path.join(ROOT, ".github", "workflows", "ci.yml")) as f:
        text = f.read()
    # Main: one group per run (no waiting run is dropped) and no cancel; a PR branch still cancels its old run.
    assert "group: ci-${{ github.ref == 'refs/heads/main' && github.run_id || github.ref }}-" in text
    assert "cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}" in text
