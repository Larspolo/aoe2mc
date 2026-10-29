"""operator_check.account_checks: one line per Claude account of the secrets (#4240)."""
import json

import operator_check

SECRETS = {"CLAUDE_CODE_OAUTH_TOKEN": "t0", "PACER_URL_MAIN": "u", "PACER_TOKEN_MAIN": "k",
           "ALL_SECRETS": json.dumps({"CLAUDE_CODE_OAUTH_TOKEN_BOB": "tb", "PACER_URL_BOB_MAIN": "ub",
                                      "PACER_TOKEN_BOB_MAIN": "kb"})}


def test_one_line_per_account_and_a_failed_read_is_named():
    def read(token):
        if token == "tb":
            raise TimeoutError("no answer")
        return {"five_hour": (0.4, 0, "allowed")}
    checks = operator_check.account_checks(SECRETS, read)
    assert len(checks) == 2
    (first, ok0, text0), (bob, ok1, text1) = checks
    assert ok0 and "40%" in text0 and "fires main" in text0
    assert bob == "account bob" and not ok1 and "no quota read" in text1 and "no answer" in text1
    lines, code = operator_check.report(checks)
    assert code == 1 and any(line.startswith("PROBLEM account bob") for line in lines)
