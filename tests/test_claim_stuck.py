"""framework/tools/claim.py --stuck: the `in-progress` tickets of stopped runs, also when bots keep their PR busy."""
import subprocess

import claim

NOW = 1_800_000_000
MIN = 60


def test_old_beat_is_stuck_and_a_recent_beat_is_not():
    tickets = {2160: NOW - 2 * MIN, 2617: NOW - 4 * MIN}       # Unconflict changed the ticket's PR 2 minutes ago
    tips = {2160: ("Beat #2160 by run-a", NOW - 354 * MIN), 2617: ("Beat #2617 by run-b", NOW - 3 * MIN)}
    assert claim.stuck(tickets, tips, NOW) == [(2160, "Beat #2160, 354 min ago")]


def test_released_claim_with_the_label_left_is_stuck():
    tips = {2278: ("Release #2278 by run-a", NOW - 40 * MIN)}
    assert claim.stuck({2278: NOW}, tips, NOW) == [(2278, "Release #2278, 40 min ago")]
    tips = {2278: ("Release #2278 by run-a", NOW - 1 * MIN)}    # the run removes the label now
    assert claim.stuck({2278: NOW}, tips, NOW) == []


def test_ticket_without_a_claim_ref_uses_its_own_time():
    assert claim.stuck({2049: NOW - 31 * MIN}, {}, NOW) == [(2049, "no claim, 31 min ago")]
    assert claim.stuck({2049: NOW - 5 * MIN}, {}, NOW) == []


def test_tips_reads_the_highest_slot(tmp_path, monkeypatch):
    remote, work = tmp_path / "remote.git", tmp_path / "work"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", str(work)], check=True)
    monkeypatch.chdir(work)
    claim.git("remote", "add", "origin", str(remote))
    for ref, text in (("claim/7", "Claim #7 by run-a"), ("claim/7-2", "Claim #7 by run-b"),
                      ("claim/8", "Release #8 by run-c")):
        sha = claim.git("-c", "user.name=t", "-c", "user.email=t@t", "commit-tree", claim.EMPTY_TREE,
                        "-m", text).stdout.strip()
        claim.git("push", "-q", "origin", f"{sha}:refs/heads/{ref}")
    found = claim.tips()
    assert {n: line for n, (line, _) in found.items()} == {7: "Claim #7 by run-b", 8: "Release #8 by run-c"}
