"""The repository's docs, read for the tests that check them. The module holds:

- read(*parts): the text of any file of the repository;
- agents_md(), guide_md(), story_md(), skill(name), rule(name), agent(name): the text of AGENTS.md, the guide, the
  story (`docs/agent-workflow.md`), a skill, a rule or an agent file;
- flat(text), section(text, heading), headings(text), without_code(markdown), bare_tags(markdown): what a test reads
  in a text;
- repo_files(), repo_texts(), repo_docs(): the repository's files, and the texts read as docs.

It imports no test module, so a test file that imports these loads no other test file with them."""

import functools
import os
import re
import subprocess
from pathlib import Path

from conftest import ROOT

# the files whose text, comments included, is read as docs: `repo_texts`, and `docs.md`'s paths (REVIEW.md AGT-86)
DOC_SUFFIXES = ('.md', '.py', '.ini', '.toml')
# this module's names that read no doc: a test importing only these reads none (test_review_lookup.py's docs gate)
NOT_DOC_READERS = frozenset({'flat', 'section', 'headings', 'without_code', 'bare_tags', 'repo_files', 'DOC_SUFFIXES'})
# an HTML open tag as CommonMark reads one, such as `<date>` or `<new ID>`: GitHub drops one it doesn't know. A
# placeholder that isn't a tag's form, such as `<scope, e.g. a diff>`, shows as written
HTML_TAG = re.compile(
    r'<[A-Za-z][A-Za-z0-9-]*(?:\s+[A-Za-z_:][\w.:-]*(?:\s*=\s*(?:[^\s"\'=<>`]+|\'[^\']*\'|"[^"]*"))?)*\s*/?>'
)


def read(*parts: str) -> str:
    """The text of the repository's file at the path `parts` make."""
    return Path(ROOT, *parts).read_text(encoding='utf-8')


def agents_md() -> str:
    return read('AGENTS.md')


def guide_md() -> str:
    return read('mcp_server', 'GUIDE.md')


def story_md() -> str:
    """The text of the story of how the lead and its subagents work, told for other repositories."""
    return read('docs', 'agent-workflow.md')


def skill(name: str) -> str:
    """The text of the skill `name`."""
    return read('.claude', 'skills', name, 'SKILL.md')


def rule(name: str) -> str:
    """The text of `.claude/rules/<name>`."""
    return read('.claude', 'rules', name)


def agent(name: str) -> str:
    """The text of the agent `name`'s file."""
    return read('.claude', 'agents', '%s.md' % name)


def flat(text: str) -> str:
    """`text` with each run of whitespace made one space."""
    return ' '.join(text.split())


def section(text: str, heading: str) -> str:
    """The part of `text` after the line `heading`, up to the next level-2 heading."""
    return text.split('\n%s\n' % heading, 1)[1].split('\n## ', 1)[0]


def headings(text: str) -> set[str]:
    """The level-2 and deeper heading lines of the Markdown `text`, code blocks left out."""
    return set(re.findall(r'(?m)^##+ .*$', without_code(text)))


def without_code(markdown: str) -> str:
    """`markdown` without its fenced code blocks."""
    return re.sub(r'(?ms)^```.*?^```', '', markdown)


def bare_tags(markdown: str) -> list[str]:
    """The HTML tags (HTML_TAG) of `markdown` outside its code, inline code and comments: what GitHub reads as tags.
    Inline code is read per paragraph, as it can't span a blank line: a lone backtick then pairs no later one."""
    shown = re.sub(r'(?s)<!--.*?-->', '', without_code(markdown))
    return [tag for part in re.split(r'\n[ \t]*\n', shown) for tag in HTML_TAG.findall(re.sub(r'`[^`]*`', '', part))]


def repo_files() -> list[str]:
    """The repo's files: git's list (tracked and untracked, not ignored), or without git (a zip
    download, no git installed) a walk of the tree minus the venv and caches: a failed git used
    to give an empty list, and test_constants.py's scan passed checking nothing (REVIEW.md TST-96)."""
    try:
        listed = subprocess.run(
            ['git', 'ls-files', '--cached', '--others', '--exclude-standard'], cwd=ROOT, capture_output=True, text=True
        )
        if listed.returncode == 0 and listed.stdout.split():
            return listed.stdout.split()
    except OSError:
        pass
    skip = {'.git', 'venv', '__pycache__', '.mypy_cache', '.ruff_cache', '.pytest_cache'}
    found = []
    for folder, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in skip]
        found += [os.path.relpath(os.path.join(folder, f), ROOT) for f in files]
    return found


@functools.cache
def repo_texts() -> tuple[tuple[str, str], ...]:
    """The repository's Markdown and Python files and its tool configs, each with its text. Left out: REVIEW.md, whose
    entries keep the wording they were written in, and PLAN.md, the lead's own account of the branch."""
    return tuple(
        (name, read(name))
        for name in repo_files()
        if name.endswith(DOC_SUFFIXES) and name not in ('REVIEW.md', 'PLAN.md') and Path(ROOT, name).is_file()
    )


def repo_docs() -> tuple[tuple[str, str], ...]:
    """The Markdown files of `repo_texts`, each with its text."""
    return tuple((name, text) for name, text in repo_texts() if name.endswith('.md'))
