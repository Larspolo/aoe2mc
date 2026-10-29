"""The pacer reports the flow brake with one tooling issue that asks for a faster CI (#4301)."""
import pacer


def fake(open_titles):
    made = []

    def api(path, method="GET", data=None):
        if method == "POST":
            made.append(data)
            return {"number": 99}
        return [{"title": t} for t in open_titles]
    return api, made


def test_a_brake_opens_one_issue():
    api, made = fake(["Other"])
    assert pacer.brake_ticket("brake: CI queue 6 >= 5", api) == 99
    assert made[0]["title"] == pacer.BRAKE_TITLE and "tooling" in made[0]["labels"]
    assert "CI queue 6" in made[0]["body"]


def test_an_open_brake_issue_gets_no_copy():
    api, made = fake([pacer.BRAKE_TITLE])
    assert pacer.brake_ticket("brake: CI queue 6 >= 5", api) is None and not made
