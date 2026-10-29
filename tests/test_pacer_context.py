"""The `context:` line of a pacer brief (#4190): the limit of `more.md`, higher near the hourly start limit."""
import pacer


def test_context_limit_rises_near_the_hourly_limit():
    near = int(pacer.HOURLY * 0.8)
    assert pacer.context_limit("main", {}) == pacer.CONTEXT
    assert pacer.context_limit("main", {"main": near - 1}) == pacer.CONTEXT
    assert pacer.context_limit("main", {"main": near}) == pacer.CONTEXT_HIGH
    assert pacer.context_limit("haiku", {"main": near}) == pacer.CONTEXT
    assert pacer.CONTEXT_HIGH > pacer.CONTEXT


def test_the_brief_has_the_context_line():
    text = pacer.brief({"number": 3, "title": "T", "body": "b"}, [], "pacer-r1", "main", "Usage: u", context=12345)
    assert "\ncontext: 12345\n" in text.split("--- ticket")[0] + "\n"
