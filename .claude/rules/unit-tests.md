---
paths:
  - "tests/unit/**/*"
---

# Unit tests

The rules for the unit tests (AGENTS.md, Running the tests, points here). The commands: `.claude/rules/python.md`.

**A unit test that depends on the system** says which systems it runs on, and skips elsewhere: a `skipif` on
`sys.platform`, with the reason. Such a test sets the platform itself, uses what only Unix has (`fcntl`,
`os.getuid`, `signal.SIGKILL`), or checks what only macOS does. `tests/unit/test_windows_simulation.py` runs the test
files that mention the system, or a name Unix has and Windows lacks that this code uses, with the platform set to
`win32` and those names taken away (`tests/unit/windows_simulation.py` lists them). In that run, a text-mode write
through `open` that gives no `newline` ends each line with `\r\n`, as on Windows. A read-write mode (`+`) is left as
it is. It fails on a test that then fails unmarked, and on a `win32` case skipped. It simulates only those differences:
a test that depends on Windows in another way shows only in a run there (ROADMAP item 18).

**Patching.** The repo's `.idea` marks `client`, `mcp_server`, `tests` and `tests/unit` as PyCharm's source roots,
also Designer's own `sd` and PySide6 folders, which the interpreter `mcp_server/venv` lacks (README.md, Working in
PyCharm). Tests patch a module loaded from its file with `monkeypatch.setitem(vars(module), 'NAME', value)`, not
`setattr` (PyCharm checks that name against the fixture and reports it missing); standard modules are patched
directly (`time`, not `server.time`). Unit tests replace a name of the server with `patch_server`
(`tests/unit/conftest.py`), which patches every module binding it: patching `server` alone doesn't reach the tools.
