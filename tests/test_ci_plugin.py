"""CI: the quick job compiles the Paper plugin when a change touches game/plugin (#2437), so that a compile error of
two green PRs (#2418) does not wait for the night run."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_the_quick_job_compiles_a_changed_plugin():
    with open(os.path.join(ROOT, ".github", "workflows", "ci.yml")) as f:
        text = f.read()
    quick = text.split("\n  quick:\n")[1].split("\n  sweep:\n")[0]
    assert "git diff --quiet HEAD^1 -- game/plugin" in quick           # only a change of the plugin compiles it
    step = quick.split("- name: Compile the Paper plugin")[1]
    assert "if: steps.plugin.outputs.changed" in step and "working-directory: game/plugin" in step
    assert "./gradlew --no-daemon -q jar" in step                      # as game/run.py builds it
    assert 'java-version: "25"' in quick
