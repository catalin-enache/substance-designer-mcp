"""REVIEW.md PLG-3: a client must wait at least as long as the plugin keeps a queued job, plus the
script's own time, or a job it gave up on can still start later with nobody waiting."""
import importlib.util
import os
import re
import socket
import sys

import pytest

from conftest import ROOT, server
from project_constants import PLUGIN_PACKAGE_DIR


def _plugin_queue_wait():
    with open(os.path.join(PLUGIN_PACKAGE_DIR, '__init__.py'), encoding='utf-8') as f:
        return int(re.search(r'^QUEUE_WAIT = (\d+)', f.read(), re.M).group(1))


def _sd_run():
    spec = importlib.util.spec_from_file_location('sd_run_under_test', os.path.join(ROOT, 'client', 'sd_run.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_clients_know_the_plugins_queue_wait():
    import project_constants
    assert project_constants.QUEUE_WAIT == _plugin_queue_wait()


@pytest.mark.parametrize('timeout', [None, 2, 120, 600])
def test_server_waits_for_the_queue_and_the_script(monkeypatch, timeout):
    waits = []
    monkeypatch.setattr(server, '_send', lambda request, wait: waits.append(wait) or {'ok': True, 'output': 'x'})
    server._bridge('print(1)', timeout=timeout)
    assert waits[0] >= _plugin_queue_wait() + (timeout or 0)


@pytest.mark.parametrize('args, timeout', [([], 0), (['--timeout', '10'], 10)])
def test_sd_run_waits_for_the_queue_and_the_script(monkeypatch, args, timeout):
    sd_run = _sd_run()
    waits = []
    monkeypatch.setattr(sd_run, 'send', lambda request, wait: waits.append(wait) or {'ok': True, 'output': '', 'error': ''})
    monkeypatch.setattr(sys, 'argv', ['sd_run.py', '-c', 'print(1)', *args])
    sd_run.main()
    assert waits[0] >= _plugin_queue_wait() + timeout


def test_sd_run_reports_a_timeout_without_a_traceback(monkeypatch, capsys):
    sd_run = _sd_run()

    def no_reply(request, wait):
        raise socket.timeout('timed out')
    monkeypatch.setattr(sd_run, 'send', no_reply)
    monkeypatch.setattr(sys, 'argv', ['sd_run.py', '-c', 'print(1)'])
    with pytest.raises(SystemExit) as stop:
        sd_run.main()
    assert stop.value.code == 1 and 'No reply from Designer' in capsys.readouterr().err
