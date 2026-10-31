"""`tokens.phase()`: the server check tools are verify, and a beat in a command does not make it a claim (#5424)."""
import tokens


def test_check_tools_are_verify():
    for cmd in ("python3 tools/tutorial_check.py W --steps 9", "python3 tools/play_check.py W",
                "timeout 900 python3 game/run.py out/W --mode standard > s.log 2>&1"):
        assert tokens.check(cmd) == "check tool"
        assert tokens.phase("Bash", {"command": cmd}) == "verify"


def test_a_beat_takes_the_phase_of_the_rest_of_the_command():
    beat = "python3 framework/tools/claim.py 5228 --beat >/dev/null; "
    assert tokens.phase("Bash", {"command": beat + "python3 tools/tutorial_check.py W"}) == "verify"
    assert tokens.phase("Bash", {"command": beat + "sed -n 1,40p game/gather.py"}) == "read"
    assert tokens.phase("Bash", {"command": "python3 framework/tools/claim.py 5228 --beat && echo rc=$?"}) == "read"


def test_the_claims_stay_claims():
    for cmd in ("python3 framework/tools/claim.py 5228", "python3 framework/tools/claim.py 5228 --or 5229 5230",
                "python3 framework/tools/cycle_start.py --lane deep", "python3 framework/tools/claim.py 5228 --release"):
        assert tokens.phase("Bash", {"command": cmd}) == "claim"
