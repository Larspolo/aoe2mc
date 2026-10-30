"""The switch of the pacer loop (#4349): another value stops the loop, a missing key is an error, not a quiet stop."""
import pacer
import pytest


def test_the_switch_is_on_only_for_workflow():
    assert pacer.switch({"pacing": {"pacer": "workflow"}})
    assert not pacer.switch({"pacing": {"pacer": "off"}})


@pytest.mark.parametrize("config", [{}, {"pacing": {}}])
def test_a_missing_key_raises(config):
    with pytest.raises(KeyError):
        pacer.switch(config)


@pytest.mark.parametrize("config, code", [({"pacing": {"pacer": "workflow"}}, 0), ({"pacing": {"pacer": "session"}}, 3)])
def test_the_option_gives_the_exit_code_of_the_loop(monkeypatch, config, code):
    monkeypatch.setattr(pacer.usage, "CONFIG", config)
    with pytest.raises(SystemExit) as e:
        pacer.main(["--switch"])
    assert e.value.code == code


def test_the_option_fails_with_a_text_when_the_key_is_missing(monkeypatch):
    monkeypatch.setattr(pacer.usage, "CONFIG", {"repo": "a/b"})
    with pytest.raises(SystemExit) as e:
        pacer.main(["--switch"])
    assert "[pacing]" in e.value.code                   # a text: exit 1
