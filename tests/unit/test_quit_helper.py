"""quit_designer inside Designer (designer_helpers/quit.py): Designer's windows closed once the bridge has sent the
call's reply, with sd and PySide6 faked (REVIEW.md SRV-151)."""

import os
import sys
import types
from collections.abc import Callable
from typing import cast
from unittest import mock

import pytest


@pytest.fixture
def helpers(faked_helpers: types.ModuleType) -> types.ModuleType:
    vars(faked_helpers)['_PM'] = mock.Mock(getUserPackages=list)
    return faked_helpers


def _timer() -> mock.MagicMock:
    return cast(mock.MagicMock, sys.modules['PySide6.QtCore'].QTimer)


def test_the_windows_are_closed_once_the_reply_is_sent_not_after_a_time(helpers: types.ModuleType) -> None:
    # it closed them 300 ms after the call returned, so the bridge could still reply: a time (`.claude/rules/waits.md`)
    handed: list[Callable[[], object]] = []  # what the helper handed _after_reply; its result is dropped
    vars(helpers)['_after_reply'] = handed.append  # the plugin's, in the job's scope
    _timer().singleShot.reset_mock()
    helpers.quit_designer(os.getpid(), 'closed')
    assert len(handed) == 1 and callable(handed[0])
    assert not _timer().singleShot.called


def test_with_an_older_plugin_they_are_closed_300_ms_after(helpers: types.ModuleType) -> None:
    # a plugin installed before _after_reply, until Designer restarts with the new one
    vars(helpers).pop('_after_reply', None)
    _timer().singleShot.reset_mock()
    helpers.quit_designer(os.getpid(), 'closed')
    assert _timer().singleShot.call_args.args[0] == 300
