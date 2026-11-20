---
paths:
  - "**/*.md"
  - "**/*.py"
  - "**/*.ini"
  - "**/*.toml"
---

# The docs tests

The docs tests, the tests that validate the docs, are the tests of a change of Markdown files, the skills and agents
included, alone or with code (AGENTS.md, Running the tests, points here). They run too on a change of a comment or a
docstring in a `.py`, `.ini` or `.toml` file, which they also check (`docs_text.DOC_SUFFIXES`; the user, 2026-11-20).
With code, they run beside the code's tests. Docs changed alone, in a commit or a whole branch, run only these, the
final check included. Docs changed alone means a change of Markdown files only (the user, 2026-11-20). A change of a
comment or a docstring, even with nothing else changed, is a change of code, so the final check runs both full suites
for it. Lint and types run with the docs tests as always, `tests/unit/test_lint.py tests/unit/test_types.py` added to
this command:
`mcp_server/venv/bin/python -m pytest tests/unit/test_agents.py tests/unit/test_constants.py tests/unit/test_guide.py tests/unit/test_large_reads.py tests/unit/test_review_lookup.py tests/unit/test_server.py`
(`test_review_lookup.py` fails if a test that reads a doc is missing from this command).
