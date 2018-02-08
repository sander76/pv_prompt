import pytest

from pv_prompt.async_prompt import BasePrompt


def another_method():
    pass


def test_toolbar_string():
    ts = BasePrompt('', 1, 2)
    _str = ts._toolbar_string()
    assert _str == "(q) quit"

    ts.register_commands({'a': another_method})
    _str = ts._toolbar_string()
    assert _str == "(q) quit | (a) another_method"
