"""framework/tools/cycle_start.py names the merged fix of a red night run (#3229)."""
import cycle_start as start


def rec(subject, body=""):
    return f"{subject}\x1f{body}\x1e\n"          # the format of `git log` in main()


def test_a_commit_that_closes_a_closed_fix_main_ticket_is_named():
    log = rec("Put a roof over the militia floor of the elevation test", "Closes #3212")
    assert start.merged_fix(log, {3212}) == "Put a roof over the militia floor of the elevation test (#3212)"


def test_no_such_commit_gives_no_line():
    assert start.merged_fix(rec("Free the town centers", "Closes #3222"), {3212}) == ""
    assert start.merged_fix("", set()) == ""


def test_a_fix_main_commit_is_named_by_its_subject():
    assert start.merged_fix(rec("Fix main: the mc test of the roof"), set()) == "Fix main: the mc test of the roof"


def test_the_newest_fix_wins():
    log = rec("Free the town centers", "Closes #3222") + rec("Put a roof", "Closes #3212") + rec("Fix main: old")
    assert start.merged_fix(log, {3212}) == "Put a roof (#3212)"
