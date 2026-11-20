"""The parser of the shell command lines that the hook in `large_reads.py` sizes and counts (REVIEW.md AGT-101). It
splits a line into its simple commands, finds the folder a `cd` moves the shell to, and gives the lines `cat`, `head`,
`tail` and `sed -n` print of each file. The docstring of `large_reads.py` says which forms the hook sizes, and what was
measured in Claude Code's shell.

The hook imports this module only where a Bash call needs it. A hook without this file then lets every Bash call
through, as any error inside its `main()` does. Its Read and web refusals don't use this module, and still apply."""

import os
import re
import shlex
from collections.abc import Callable

# between commands whose outputs add up: both sides of ||, though the right one runs only when the left one fails
SEPARATORS = (';', '&&', '||')
PIPED = (*SEPARATORS, '|')  # between the commands of a Bash call that only reads (`_only_reads` in large_reads.py)
OPERATORS = '();<>|&'  # shlex's punctuation: a word starts after one, as after a blank
EXPANDED = frozenset('*?[{~$`')  # a word holding one may name other files once the shell expands it
SED_LINES = re.compile(r'(\d+)(?:,(\d+|\$))?p')  # sed -n's script: Ap, A,Bp or A,$p
DEFAULT_COUNT = '10'  # the lines head and tail print without a count
FOLLOWED = ('cd', 'chdir')  # zsh's chdir is cd: `cd DIR` and `chdir DIR` move the folder the hook finds files from
# a `..` of an absolute path: a name of its own, between the separators of a path (`/`, and `\` on Windows) or at its end
DOTS = re.compile(r'(?<=[{0}])\.\.(?=[{0}]|$)'.format(re.escape(os.sep + (os.altsep or ''))))
# the commands that may move the shell's folder where the hook doesn't follow it: a cd in another form, and the
# builtins and reserved words that run other words in the shell. A function or a shell option moves the folder without
# ending the sizing (the docstring of `large_reads.py`)
MOVES = frozenset((*FOLLOWED, 'pushd', 'popd', 'eval', 'source', '.', 'repeat'))
# the words zsh reads before the command it runs in the shell, besides an assignment (ASSIGNMENT): precommand modifiers
# and reserved words. A cd after one moved zsh's folder (2026-11-19)
BEFORE = frozenset(
    ('builtin', 'noglob', 'nocorrect', '-', 'time', '!', '{', 'if', 'elif', 'then', 'else', 'while', 'until', 'do')
)
ASSIGNMENT = re.compile(r'[A-Za-z_]\w*\+?=')  # X=1 before a command

# a file a command prints, as written or as its absolute path, and the lines it prints, as Python slices a list of
# them: start and stop
Span = tuple[str, int, int | None]
# a simple command of a command line: the separator before it ('' for the first), and its words
Command = tuple[str, list[str]]


def spans(command: str, cwd: str) -> list[Span] | None:
    """The files the commands of `command` print, each by its absolute path from `cwd`, as the `cd`s before it moved
    it, with the lines printed of it, up to a command of MOVES that the hook doesn't follow. None for a command line the
    hook can't size: one `commands` refuses, a form of a printer it doesn't size, a printer reading stdin, or an option
    or a word the shell expands among a printer's files."""
    found = commands(command)
    if found is None:
        return None
    joins = [join for join, _ in found]
    printed: list[Span] = []
    for i, (_, words) in enumerate(found):
        program, args = words[0], words[1:]
        if program in PRINTERS:
            files = PRINTERS[program](args)
            if not files:  # a form it doesn't size, or no file: the program reads stdin
                return None
            for file, start, stop in files:
                path = _named(cwd, file)
                if path is None:
                    return None
                printed.append((path, start, stop))
            continue
        followed = program in FOLLOWED and len(args) == 1 and _ran_before(joins[i:])
        folder = _folder(cwd, args[0]) if followed else None
        if folder is not None:
            cwd = folder
        elif _run(words) in MOVES:
            break  # the folder is unknown from here, so the commands after it aren't sized
    return printed


def _ran_before(joins: list[str]) -> bool:
    """Whether a command has run whenever a command after it runs: `joins` holds the separator before it, then those
    after it. It always runs when it opens the line or follows `;`. After `&&` it may not run, and then only the
    commands joined by `&&` alone are skipped with it. After `||` it may not run while a later command does."""
    return joins[0] in ('', ';') or all(join == '&&' for join in joins)


def _folder(cwd: str, word: str) -> str | None:
    """The folder `cd word` moves zsh to from `cwd`, or None for a word `_named` refuses and for a cd that fails. zsh
    reads the path logically if it can: each `..` drops the name before it, if the path up to that name is a folder,
    and the path must end at a folder. Otherwise zsh reads the path physically, and the folder is given by its real
    path, as zsh's `$PWD` then names it (the docstring of `large_reads.py`)."""
    path = _named(cwd, word)
    if path is None:
        return None
    logical = os.path.normpath(path)
    before = (os.path.normpath(path[: dots.start()]) for dots in DOTS.finditer(path))  # the path up to each `..`
    if os.path.isdir(logical) and all(map(os.path.isdir, before)):
        return logical
    return os.path.realpath(path) if os.path.isdir(path) else None


def _run(words: list[str]) -> str:
    """The word zsh runs as the command of `words`: the first after the assignments and the words of BEFORE. Empty if
    there is none."""
    return next((word for word in words if word not in BEFORE and not ASSIGNMENT.match(word)), '')


def commands(command: str, separators: tuple[str, ...] = SEPARATORS) -> list[Command] | None:
    """The simple commands of `command` before its comment, joined by one of `separators` (by default `;`, `&&` or
    `||`): each the separator before it ('' for the first) and its words, with the quotes taken off. None for a command
    line holding anything else: another operator, a newline, an empty command or a quote never closed."""
    if '\n' in command or '\r' in command:
        return None
    lexer = shlex.shlex(command[: _comment(command)], posix=True, punctuation_chars=OPERATORS)
    lexer.whitespace_split = True  # words end at blanks and operators only, as in the shell
    lexer.commenters = ''  # shlex starts a comment at a # inside a word too: _comment found the shell's
    operators = frozenset(OPERATORS)  # a pipe, a redirection, a subshell, the background...
    found: list[list[str]] = [[]]
    joins = ['']  # the separator before each command
    try:
        for token in lexer:
            if token in separators:
                if not found[-1]:
                    return None
                found.append([])
                joins.append(token)
            elif token and operators.issuperset(token):
                return None
            else:
                found[-1].append(token)
    except ValueError:  # a quote never closed, or a backslash ending the line
        return None
    return [(join, words) for join, words in zip(joins, found, strict=True) if words]


def _comment(command: str) -> int:
    """Where the comment of `command` starts, as the shell finds it: at a `#` starting a word, outside quotes and not
    after a backslash. The length of `command` if it has none."""
    if '#' not in command:
        return len(command)
    quote = ''  # the quote the scan is inside, if any
    before = ' '  # the character before, outside quotes: a word starts after a blank or an operator
    i = 0
    while i < len(command):
        c = command[i]
        if quote:
            if c == quote:
                quote = ''
            elif c == '\\' and quote == '"':
                i += 1  # the escaped character
        elif c == '#' and before in ' \t' + OPERATORS:
            return i
        elif c in '\'"':
            quote = c
        elif c == '\\':
            i += 1  # the escaped character
        before = c
        i += 1
    return len(command)


def _named(cwd: str, word: str) -> str | None:
    """The absolute path `word` names from `cwd`, or None for an option or a word the shell expands."""
    path = os.path.join(cwd, word)
    return None if word.startswith('-') or EXPANDED.intersection(word) or not os.path.isabs(path) else path


def _cat(args: list[str]) -> list[Span] | None:
    """`cat FILE...`: every line of each file."""
    return [(file, 0, None) for file in args]


def _head(args: list[str]) -> list[Span] | None:
    """`head [-n N | -N] FILE...`: the first N lines of each file. BSD head reads +N as N, and refuses 0 or less."""
    count, files = _count(args)
    found = re.fullmatch(r'\+?(\d+)', count)
    if not found or int(found[1]) < 1:
        return None
    return [(file, 0, int(found[1])) for file in files]


def _tail(args: list[str]) -> list[Span] | None:
    """`tail [-n N | -N | -n +N] FILE...`: the last N lines of each file, or from line N to the end. BSD tail prints
    nothing for 0, and the whole file for +0."""
    count, files = _count(args)
    found = re.fullmatch(r'([+-]?)(\d+)', count)
    if not found:
        return None
    lines = int(found[2])
    if found[1] == '+':
        start, stop = max(lines, 1) - 1, None
    elif lines:
        start, stop = -lines, None
    else:  # -0 would slice every line
        start, stop = 0, 0
    return [(file, start, stop) for file in files]


def _count(args: list[str]) -> tuple[str, list[str]]:
    """The line count of head or tail, as written, and the words after it: `-n N`, `-nN` or `-N` opening `args`, or 10
    lines."""
    if args[:1] == ['-n'] and len(args) > 1:
        return args[1], args[2:]
    found = re.fullmatch(r'-n(.+)|-(\d+)', args[0]) if args else None
    return (found[1] or found[2], args[1:]) if found else (DEFAULT_COUNT, args)


def _sed(args: list[str]) -> list[Span] | None:
    """`sed -n 'Ap'`, `'A,Bp'` or `'A,$p'` with one FILE: line A, or lines A to B, or from line A to the end. BSD sed
    prints line A alone for B under A, and refuses line 0."""
    found = SED_LINES.fullmatch(args[1]) if len(args) == 3 and args[0] == '-n' else None
    if not found or int(found[1]) < 1:
        return None
    first = int(found[1])
    last: str = found[2] or found[1]
    return [(args[2], first - 1, None if last == '$' else max(int(last), first))]


# the programs whose output the hook sizes, each with what it prints of its arguments: None for a form it doesn't size
PRINTERS: dict[str, Callable[[list[str]], list[Span] | None]] = {
    'cat': _cat,
    'head': _head,
    'tail': _tail,
    'sed': _sed,
}
