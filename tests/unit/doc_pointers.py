"""The pointers a text gives into a doc's sections, for the test that each names a section the doc has
(test_guide.py). Its pointers into AGENTS.md take these forms, and the same for DECISIONS.md:

- "(AGENTS.md, Running the tests)", "`AGENTS.md`, Running the tests", "AGENTS.md (Running the tests)" and
  "AGENTS.md's Running the tests";
- a name in quotes after any of these, as in "AGENTS.md's \"Keep it yourself\"";
- a part of a section after the section, as in "(AGENTS.md, Working on this project: Rules for some files only)",
  or another section after "and".

A name is a label of the doc: a heading or a bold span, without a trailing `.`, `:`, `,`, quote or `...`. A pointer may
shorten it ("Start with the tests" for "Start with the tests, always (TDD)"), or go on after it in prose ("AGENTS.md,
Running the tests says"). What follows the file's name in lowercase is prose, not a name, and so is a file's name
(`.md` or `.py`). Comment markers (`#`) and quote markers (`>`) are taken off the start of each line first, so a pointer
wrapped across a comment reads as one."""

import re

from docs_text import flat, without_code

# what ends a name that isn't a whole label: a parenthesis, a comma, a colon, a semicolon, a quote, or a full stop
# ending a sentence
NAME_END = re.compile(r'[(),;:"]|\.(?:\s|$)')
# what follows a file's name in a pointer into it: ", " or " (", after "'s" or not, or "'s " alone
AFTER_FILE = r"(?:(?:'s)?(?:,\s+|\s+\()|'s\s+)"
# what goes on from a section to a part of it (": Rules", " (Rules", ", Rules"), or to another section (" and Running")
TO_PART = r'(?::\s+|\s+\(|,\s+|\s+and\s+)'
PART = re.compile(TO_PART + r'(?=["A-Z])')
# a trailing `.`, `:`, `,`, quote or `...`
TRAILING = '.:,"\' '


def labels(markdown: str) -> set[str]:
    """The headings and bold spans of `markdown`, code blocks left out, each without its trailing punctuation."""
    text = without_code(markdown)
    found: list[str] = re.findall(r'(?m)^#+\s+(.+)$', text) + re.findall(r'\*\*(.+?)\*\*', flat(text))
    return {label.rstrip(TRAILING) for label in found}


def dangling_pointers(text: str, file: str, known: set[str]) -> list[str]:
    """The names that pointers in `text` give to sections of `file`, a doc whose labels are `known`, and that name none
    of them."""
    if file not in text:
        return []
    unwrapped = flat(re.sub(r'(?m)^[ \t]*(?:#+|>+)[ \t]?', '', text))
    pointer = re.compile(r'(?<![\w/.-])`?%s`?%s' % (re.escape(file), AFTER_FILE))
    return [name for m in pointer.finditer(unwrapped) if (name := _dangling(unwrapped[m.end() :], known))]


def _dangling(rest: str, known: set[str]) -> str:
    """The name at the start of `rest` that is no label of `known`, or a part of it that is none, else ''."""
    if rest.startswith('"'):
        name = rest[1:].split('"', 1)[0].rstrip(TRAILING)
        return name if name[:1].isupper() and not _shortens(name, known) else ''
    if not rest[:1].isupper():
        return ''  # prose
    whole = [label for label in known if _begins_with(rest, label)]
    if whole:
        end = len(max(whole, key=len))
    else:
        word: str = NAME_END.split(rest, maxsplit=1)[0]  # a fresh local: split gives `str | Any`
        name = word.rstrip(TRAILING)
        if name.endswith(('.md', '.py')):
            return ''
        if not _shortens(name, known):
            return name
        end = len(name)
    part = PART.match(rest, end)
    return _dangling(rest[part.end() :], known) if part else ''


def _shortens(name: str, known: set[str]) -> bool:
    """Whether `name` is a label of `known`, or its start up to a word's end."""
    return any(_begins_with(label, name) for label in known)


def _begins_with(text: str, start: str) -> bool:
    """Whether `text` begins with `start` followed by no letter or digit."""
    return text.startswith(start) and not text[len(start) : len(start) + 1].isalnum()
