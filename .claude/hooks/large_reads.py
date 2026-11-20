"""The lead's hooks against large reads (ROADMAP item 102): they keep big files and big command outputs out of the
lead's context, and send such reads to the `analyst` agent (AGENTS.md, Delegating to subagents).

`.claude/settings.json`, the project's shared settings, registers this module five times: before a read, before a
web fetch or search, before a Bash command, and after a Bash command or a reading call, one that succeeded and one
that failed. So the hooks apply in every main session in this repository, the user's included. Claude Code runs it
with the call as JSON on stdin. The module tells the events apart by `hook_event_name`, and the calls by `tool_name`:

- **Before a read** (`Read`, and PyCharm's `mcp__pycharm__read_file`): a read that returns over 20 KB (READ_LIMIT) is
  refused, its line numbers counted. The hook exits 2 with the reason on stderr, which the lead reads. The reason
  gives the size and lines read, and the two ways on: read fewer lines with Read's `offset` and `limit`, or ask
  `analyst`. A refused `read_file` is sent to Read for a range, since its own `limit` gives none (below). The reason
  names that file by the absolute path the hook measured, which Read finds from any folder. A refused `read_file` of a
  notebook is sent to `read_file` with a smaller `limit` instead, as Read shows a notebook's cells unsized.
  - Read returns `limit` lines from line `offset`, and the whole file without either. It puts the line's number and a
    tab before each line, unpadded (READ_NUMBER).
  - PyCharm's `read_file` returns the lines from `offset` to the end of the file, cut in the middle to `limit` lines,
    2,000 without it. It puts `L<n>: ` before each line, and one line saying how many it cut in their place.
  - Both show an empty line after a last newline.
  - PyCharm's `read_file` ends a line at LF, at CRLF and at a lone CR, and its text holds no CR. A file of three lines
    ended by CRLF, and one ended by lone CRs, each showed `L1:` to `L3:` and an empty `L4: `, and `dddd` followed by CR
    and CRLF ended two lines. PyCharm's `search_regex` found no `\\r` in those files (measured 2026-11-19). So the hook
    reads a lone CR as LF and counts a CRLF as one byte for `read_file` (`_PyCharmLines`). Read ends a line only at LF:
    the file of lone CRs showed as one line.
  - These reads pass, with exit 0 and no output: the repository's own PLAN.md, which AGENTS.md says to read before
    anything else; images and PDFs (UNMEASURED), and notebooks read by Read; a range given by a value that isn't a
    whole number; a path the hook can't measure. Such a path is a missing one, one that isn't a regular file, a URL
    (`jar://`, and `file://` for Read) or an entry of an archive (`x.jar!/pkg/Foo.class`).
  - A relative path is found from the call's `cwd` for Read. Read finds a relative path after a `cd` from the folder
    the `cd` moved to: the lead's Read of `conftest.py` after `cd tests/unit` found `tests/unit/conftest.py`, and its
    Read of `tests/unit/conftest.py` found nothing (2026-11-19). For PyCharm's `read_file`, a relative path is found
    from the project: the call's `projectPath`, else the repository's root (PROJECT), the project PyCharm has open
    (`.claude/rules/python.md`).
  - Read takes the blanks off around the path, and reads a leading `~/` as the home folder: `~/x`, ` ~/x` and a tab
    before `~/x` each read the file in the home folder, and `~user/x` wasn't expanded. PyCharm's `read_file` expands no
    `~`: it found no file at `~/x` (measured 2026-11-19).
  - Read and PyCharm's `read_file` read a `..` lexically: it drops the name before it, a symlink's included. With
    `link` a symlink to a folder elsewhere, each read `link/../x` as the `x` beside `link`, while `cat` printed the `x`
    beside the link's target (measured 2026-11-20). So the hook measures the path read lexically (`_path`). A Read of
    `link/../x` passed the hook while the `x` beside the target was the big one (measured by the lead, REVIEW.md
    AGT-91): Claude Code hands the hook Read's path already read so.
  - PyCharm's `read_file` takes `file://` and an absolute path as that path, as written, and the hook sizes it so
    (FILE_URL). It read the same lines as the path did. It didn't decode `%41` in a file's name, and it found no file
    at `file://localhost/` and an absolute path, nor at `file://` and a relative one (measured 2026-11-19).
  - PyCharm's `read_file` shows a notebook (`.ipynb`) as text, numbered and cut as a file's lines. The hook rebuilds
    that text from the notebook's JSON and sizes it (`_notebook`). Measured on Jupyter's format 4 (2026-11-19):
    - each cell is a line `#%%` for code, `#%% md` for markdown, or `#%% ` and its type for another (`raw`,
      `heading`), then its source. A newline joins the cells, and a cell's outputs and metadata don't show;
    - the source is a string, or a list of strings joined. Its CRLF and CR line ends are newlines, and a `#` goes
      before a line of it starting with `#%%` (ESCAPED). `# %%`, `##%%` and `  #%%` showed as written, and Unicode's
      line separator, VT, FF and NEL broke no line. A newline ending a cell's source shows as an empty line before the
      next cell;
    - notebooks of R's and Scala's kernels showed the same markers. A notebook with an empty list of cells showed one
      empty line, as an empty file does, which the hook counts as none. One whose JSON didn't parse, or without a list
      of cells, showed `#%%` and an empty line. Format 3 showed its worksheet's cells, a code cell's source taken from
      `input`. The hook rebuilds neither: such a notebook passes, as does one with a cell whose type or source isn't
      text.
  - In a file over 1 MB (BIG), or a notebook's text over it, a read is sized only until it is known to pass
    READ_LIMIT. The reason then says "over 20 KB", without the size and lines. A line is read up to CAP bytes. Read's
    range and the first half of what `read_file` shows are read forward, from the start of the file. The last lines
    `read_file` shows are read back from the end of the file. Only when the bounds of their numbers can't tell whether
    the read passes READ_LIMIT does the hook read the lines between them. A notebook's JSON is read whole.
- **Before a web fetch or search** (`WebFetch`, `WebSearch`): the lead's is always refused, with exit 2 and the reason
  on stderr. Every web fetch and search goes to the `analyst`, even of one known page (the user, 2026-11-19). WebFetch
  reads up to 100,000 characters of a page (Claude Code's tools reference, WebFetch tool behavior). Some pages come
  back whole, the prompt ignored: a 46 KB documentation page did (2026-11-18 and 2026-11-19). Which pages come back
  whole isn't documented. A subagent's call passes, the analyst's and the developer's included (the user: "any other
  subagent should be allowed to do web search").
- **Before a Bash command:** a command that would print over 20 KB of files is refused, with exit 2 and the reason on
  stderr. The reason gives the size and lines printed. It names the files by their real paths, as a refused command's
  `cd` never ran. A real path also names the file the command prints where its path has a `..` after a symlink: `cat`
  opened `link/../x` physically, the `x` beside the link's target (measured 2026-11-20), while Read reads the `..`
  lexically (REVIEW.md AGT-91, AGT-95). The reason's ways on are fewer lines, with Read's `offset` and `limit` or
  with `head` or `sed -n`, or a question for `analyst`; it leaves Read out where a file printed is a notebook. It
  doesn't say the output would fill the context: Claude Code puts only part of a big output there (the measurements
  below).
  - A call run in the background (`run_in_background`) is never sized (the user, 2026-11-20). Its output goes to a
    file, not into the context, and the notice of its end carries none (seen by the lead, 2026-11-20). The lead reads
    that file with Read, which the hook sizes.
  - The module beside this one, `command_lines.py`, parses the command line. MOVES, BEFORE and EXPANDED below are its
    names, and so are `_folder` and `_comment`. The hook puts its own folder on Python's path (HOOKS), which Python
    leaves out with `PYTHONSAFEPATH` set.
  - Only a command line made of simple commands joined by `;`, `&&` or `||` is sized. Its commands that print files
    add up, both sides of `||` included, though the right one runs only when the left one fails:
    - `cat FILE...`: every line;
    - `head [-n N | -N] FILE...`: the first N lines of each file, 10 by default;
    - `tail [-n N | -N | -n +N] FILE...`: the last N lines of each file, 10 by default, or from line N to the end;
    - `sed -n 'Ap'`, `'A,Bp'` or `'A,$p'` with one FILE: line A, or lines A to B, or from line A to the end.
  - In a file over 1 MB (BIG), the lines a command prints are sized only until they pass READ_LIMIT, each up to CAP
    bytes, and the reason then says "over 20 KB". `tail`'s last lines are read back from the end of the file.
  - Only a command whose first word is `cat`, `head`, `tail` or `sed` is sized. A printer named by a path
    (`/bin/cat`), after an assignment (`X=1 cat`) or after another word (`command`, `env`, `exec`, `nice`, `time`)
    prints unsized.
  - `cd DIR`, or zsh's `chdir DIR`, moves the folder that the files after it are found from, starting from the call's
    `cwd`. The call's `cwd` follows a `cd` made in an earlier Bash call: after `cd tests/unit/__pycache__` in one
    call, `cat` of a 25 KB file there by its bare name was refused in the next (measured in the lead's session,
    2026-11-18).
  - Such a `cd` moves the folder for the commands after it only where it has run before each of them: when it opens
    the line or follows `;`, or when it follows `&&` and only `&&` follows it. After `||`, or after `&&` with another
    separator later, it may not run while a later command does. It then ends the sizing, as MOVES do (below).
  - With zsh's default options (`CHASE_DOTS` and `CHASE_LINKS` unset), as measured, zsh reads DIR logically where it
    can: each `..` drops the name before it, a symlink's included, if the path up to that name is a folder, and DIR
    must end at a folder. Otherwise zsh reads DIR physically, and the `cd` fails if that names no folder either. The
    hook follows DIR the same way (`_folder`). Claude Code's shell set neither option (`setopt`, 2026-11-20). Measured
    2026-11-20 in zsh 5.9, with `link` a symlink to a folder elsewhere:
    - `cd link/..` moved to the folder holding `link`, and `cd link/../sub` to the `sub` beside `link`;
    - `cd link/../only` moved to the `only` beside the link's target, when only that one existed, and
      `cd link/../q/../sub` to the `sub` there, when `q` was only there. `$PWD` then named that folder by its real
      path;
    - `cd missing/..`, `cd missing/../sub` and `cd file/..` failed, the shell's folder unmoved.
  - A command of MOVES that the hook doesn't follow ends the sizing: the commands after it aren't sized, and those
    before it are. Such a command runs one of MOVES (`cd` or `chdir` in another form, such as
    `cd -` or a missing folder, `pushd`, `popd`, `eval`, `source`, `.` or `repeat`), as its first word or after an
    assignment or the words of BEFORE (`builtin`, `noglob`, `nocorrect`, `-`, `time`, `!`, `{`, `if`, `then`, `do`
    and the like). In zsh, `builtin cd sub`, `noglob cd sub`, `nocorrect cd sub`, `- cd sub`, `X=1 cd sub`,
    `time cd sub`, `! cd sub`, `if cd sub`, `{ cd sub }`, `repeat 1 cd sub`, `eval 'cd sub'` and `source` of a script
    running `cd sub` each moved the folder, while `command cd sub`, `env cd sub`, `nice cd sub` and `coproc cd sub`
    didn't (2026-11-19).
  - A function or a shell option, from the user's profile or set earlier in the line, moves the folder unseen. Unlike
    a command of MOVES, such a move doesn't end the sizing: the files after it are sized in the folder the hook
    followed. In zsh 5.9, `function f { cd sub }; f` moved to `sub`, and `setopt chase_dots` made `cd link/..` move to
    the folder holding the link's target (2026-11-20).
  - A `#` starting a word, outside quotes and not after a backslash, begins a comment, as in the shell: the hook sizes
    the line before it (`_comment`). A quoted `'# type: ignore'` begins none.
  - A command line the hook can't size passes. The note after the command still covers its output. Such a line holds:
    - an operator other than `;`, `&&` and `||`: a pipe, a redirection, a subshell or the background. `cat big | grep
      x` doesn't put the file into the context;
    - a newline, an empty command or a quote never closed;
    - a file or a folder named by a word the shell expands (EXPANDED), such as a glob or a variable;
    - an option the hook doesn't size, such as `cat -n` or `head -c`, or another form of sed;
    - a missing file, or one that isn't a regular file.
  The command line is split by `shlex`, which takes the quotes off. It reads a quoted operator alone, such as `'|'`,
  as the operator, so such a line passes, or is split where the shell doesn't split it.
- **After a Bash command:** an output of 8,000 characters or more (OUTPUT_LIMIT) that reached the context gets a note.
  The hook prints it on stdout as the `additionalContext` of a JSON object, and exits 0. The note names the command and
  the output's size. It says to give the next command of that kind to `analyst`, or to learn the size of its output
  first.
  - After a command that succeeded (PostToolUse), the output is stdout and stderr together. An output Claude Code saved
    to a file gets no note, since only a preview of it reached the context.
  - After a command that failed (PostToolUseFailure), the output is in `error`, after its first line, `Exit code N`.
    `error` keeps about 10,000 characters of it (FAILURE_CUT): past that, the note gives the size as "at least".
  - After a call run in the background, the note sizes what the call returned as it started. Its output went to a
    file (Before a Bash command).
- **After a reading call:** the lead's 8th reading call of a turn, and each 8th after it (RESEARCH_READS), gets a
  note, printed as the note after a Bash command is: if this is research, hand the rest to `analyst`. The size checks
  stop one big read, but not many small ones adding up. The note never blocks, as some work needs many reads (the
  user, 2026-11-19). One call can get both notes, in one `additionalContext`.
  - A reading call is a Read, a Grep or a Glob, PyCharm's `read_file`, `search_text`, `search_regex`, `search_file`,
    `search_symbol`, `get_symbol_info`, `analyze_calls` or `list_directory_tree` (READING_TOOLS), or a Bash call that
    only reads (`_only_reads`). A call that failed counts too.
  - A Bash call only reads when the call doesn't run in the background, and each simple command of its line, split at
    `|`, `||`, `&&` and `;`, starts with a program that reads: one of READERS, git with one of GIT_READS (also after
    `-C <dir>`), or a Python of PYTHONS running LOOKUP. A line holding a redirection into a file, a `$(` or a backtick
    doesn't count, nor one the hook can't split, such as one with a newline. The test is approximate, as it only feeds
    a note: `sed -i` or `find -delete` count as reads.
  - A turn is told by the payload's `prompt_id`. A turn starts with a message of the user's, or with a notification
    such as a subagent's report, and each turn has a `prompt_id` of its own: in a turn a subagent's report started, the
    count was 1 after one Read, after more than 16 counted calls in the user's prompt before it (measured by the lead,
    2026-11-19). A PostToolUse payload carries `session_id` and `prompt_id`, and a Read and a Bash call made for one
    prompt of the user's had the same `prompt_id`, a later prompt another (measured by the lead with a probe hook,
    2026-11-19). A PostToolUseFailure payload carries both too: measured in a subagent's calls, and in the lead's,
    whose count went from 4 to 5 across a failing `ls` (2026-11-19).
  - The count is kept in one small file per session in the system's temporary folder (`tempfile.gettempdir()`, or
    STATE_FOLDER when set), `large_reads_<session_id>.json`, holding only the turn's `prompt_id` and its count. The
    files stay there, and the system clears that folder. Another `prompt_id`, or a file cut short, starts the count
    from 1. A payload without `prompt_id`, or whose `session_id` isn't a plain name, isn't counted, and neither is a
    call whose count can't be written.
  - Calls counted at once may each read the count before another writes it, so a note may come late, or more than
    once. A call that reads the file while another rewrites it finds it cut short, and its count restarts at 1.

All of them let a subagent's calls through, and count none of them: a large read inside `analyst` is its job. A
subagent's payload has `agent_id`.

The hook fails open: any error inside `main()` lets the call through, with exit 0 and no output. Claude Code reads a
hook's exit 2 as a block, and Python exits 2 when it can't open its script. So the command in `.claude/settings.json`
checks first that the script exists, or a missing script would block every read. It also checks that the venv's Python
exists: in a clone without the venv, the shell would exit 127 on every call. Any exit other than 0 and 2 is a
non-blocking error: the call goes through.

Measured with a probe hook logging the payloads (2026-11-18):

- a Read's `tool_input` holds only `file_path` for a whole read, and adds `offset` and `limit` for a ranged one.
  PyCharm's `read_file` takes the same three, and its `file_path` may also be relative to the project, or a URL. Its
  schema also takes the project's folder, `projectPath`;
- the lead's payloads carry no `agent_id`. Claude Code's docs say a subagent's carry `agent_id` and `agent_type`;
- Edit accepts a file read only by a range, so refusing whole reads doesn't block editing;
- a Bash call's `tool_response` holds `stdout`, `stderr`, `interrupted`, `isImage` and `noOutputExpected`. A 10 KB
  output arrived whole, and all of it reached the context. A 60 KB output was saved to a file: `tool_response` gained
  `persistedOutputPath` and `persistedOutputSize`, `stdout` was cut to 30,000 characters, and the context got only a
  2 KB preview;
- a PostToolUse hook whose script had been deleted exited 2, and Claude Code reported a blocking error.

Measured with a probe hook in `.claude/settings.local.json`, in the lead's session (2026-11-19):

- a Bash call that exits non-zero gets no PostToolUse event. It gets PostToolUseFailure, matched by `Bash` as usual.
  Besides `session_id` and `prompt_id`, which the count reads (above), its payload holds `cwd`, `duration_ms`,
  `effort`, `error`, `hook_event_name`, `is_interrupt`, `permission_mode`, `tool_input`, `tool_name` and
  `tool_use_id`, and no `tool_response`;
- `error` is `Exit code N` and a newline, then the output, stdout and stderr together, cut to about 10,000
  characters: `printf 'small-failing-output\n'; exit 5` gave 32 characters, and a 40,001-character output with
  `exit 6` gave 10,040;
- the note printed as PostToolUseFailure's `additionalContext` reached the lead's context;
- a failed call's output is never saved to a file. The context got about 20 KB of the 40,001-character output, with
  `[20012 characters truncated]` in the middle;
- after an edit of a settings file, the first Bash call ran without the new hook, and the next one had it;
- with `bashOutputMaxChars` at 10,000 (Claude Code's setting, 30,000 by default), a successful 12,000-character
  output was saved to a file and the context got only a 2 KB preview, while a failing 15,000-character one reached the
  context whole. `.claude/settings.json` sets that cap, so a successful command can't put more than 10,000 characters
  into the context; the note after a command still covers the failing ones. The cap applies in subagents too: an
  `analyst`'s successful 12,000-character output was saved the same way.

Measured by reading a file of 2,100 numbered lines (2026-11-18):

- Read's `offset` is the first line, 1-based, and `limit` the number of lines. `offset` alone read to the end, past
  2,000 lines, and `limit` alone from the first line. An `offset` of 0 or less read from the first line, and a `limit`
  of 0 or less to the end;
- PyCharm's `read_file` read from `offset` to the end, and showed at most `limit` lines, 2,000 without it: the first
  half of `limit` from `offset`, a line saying how many were cut, and the rest from the end of the file. `offset=10,
  limit=5` showed lines 10, 11, 2099, 2100 and 2101. Line 2101 was the empty line after the last newline, which
  `read_file` numbers. An `offset` under 1, or a `limit` under 1 or over 5,000, got an error and no lines. So did an
  `offset` past the file's last line: `offset=10000, limit=1` on `mypy.ini`, far shorter, got only the error `offset
  exceeds file length` (measured by the lead, 2026-11-20). The first `offset` that got it was one past the last line,
  the empty line after a last newline counted, as `_has_line` takes it. On a file of `a`, a newline and `b`,
  `offset=2` showed `L2: b` and `offset=3` got the error. With a newline after `b`, `offset=3` showed the empty
  `L3: ` and `offset=4` got it (measured by the lead, 2026-11-20).

The lines' numbers (2026-11-19):

- Read's tool description says it returns its lines "in cat -n format, with line numbers starting at 1", and cat -n
  pads each number to 6 characters. Read doesn't: the lead's Read of `tests/unit/conftest.py` returned its first line
  after `1` and a tab, with no spaces before them (REVIEW.md AGT-19, measured by the lead);
- PyCharm's `read_file` puts `L<n>: ` before each line, and shows one line, `…<N> lines truncated…`, in place of the
  lines it cut. A notebook read with `limit=4` showed `L1: #%%`, `L2: x = 0`, `…896 lines truncated…`,
  `L899: x = 299` and `L900: ` (measured by the lead);
- a whole Read of a file of 2,005 lines returned all of them, and an empty line 2006 after the last newline. An
  `offset` alone showed that line too. Read took a relative path, `mypy.ini`, as the file in the session's folder.

Measured in Claude Code's shell (2026-11-18): zsh 5.9, not interactive, runs macOS's `/bin/cat`, `/usr/bin/head`,
`/usr/bin/tail` and `/usr/bin/sed`, and a `#` at the start of a word begins a comment. BSD head reads `-n +N` as N,
and refuses a count of 0 or less. BSD tail's `-n 0` prints nothing, and `-n +0` the whole file. BSD sed's `A,Bp` with
B under A prints line A alone, and sed refuses line 0.
"""

import collections
import functools
import io
import itertools
import json
import math
import os
import re
import stat
import sys
from collections.abc import Buffer, Callable, Iterable, Iterator
from typing import BinaryIO, NamedTuple

READ_LIMIT = 20_000  # bytes: a read or a command line that returns more is refused
BIG = 1_000_000  # bytes: a file bigger is sized only until a read or a command passes READ_LIMIT
CAP = READ_LIMIT + 1  # bytes of a line of a file over BIG that the hook reads at most: enough to pass READ_LIMIT
# bytes the hook reads of a file at a time, forward and back from its end: a fixed size, as Python's default buffer
# grew from 8 KiB to 128 KiB in 3.14
BLOCK = 8192
OUTPUT_LIMIT = 8_000  # characters of a Bash output: one this big gets a note
FAILURE_CUT = 10_000  # characters of a failed command's output that `error` keeps, about: the note says "at least"
EXIT_CODE = re.compile(r'\AExit code \d+\n')  # how a failed command's `error` starts, before its output
COMMAND_SHOWN = 80  # the note shows at most this many characters of the command
# this file's folder, which holds its parser (command_lines.py). Python puts it first on the path of the script it runs,
# but not with PYTHONSAFEPATH set, so the hook puts it there itself (REVIEW.md AGT-103)
HOOKS = os.path.dirname(os.path.realpath(__file__))
if HOOKS not in sys.path:
    sys.path.insert(0, HOOKS)
# the repository's root: PyCharm's project, where its read_file finds a relative path
PROJECT = os.path.dirname(os.path.dirname(HOOKS))
# the repository's own PLAN.md, which AGENTS.md says to read before anything else: its reads pass, whole or not
PLAN = os.path.join(PROJECT, 'PLAN.md')
UNMEASURED = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.pdf')  # Read shows them as images and pages
NOT_PATHS = ('://', '!/')  # a URL (jar://, file://), or an entry of an archive (x.jar!/pkg/Foo.class)
READ_NUMBER = '%d\t'  # what Read puts before each line, unpadded (measured 2026-11-19)
PYCHARM_READ = 'mcp__pycharm__read_file'
FILE_URL = 'file://'  # read_file reads `file://` and an absolute path as that path (measured 2026-11-19)
NOTEBOOK = '.ipynb'  # Read shows a notebook as cells, unmeasured, and read_file as text the hook rebuilds
LONE_CR = re.compile(rb'\r(?!\n)')  # a CR no LF follows: read_file ends a line there, as at LF (measured 2026-11-19)
CELL_MARKERS = {'code': '#%%', 'markdown': '#%% md'}  # the line before a cell's source; another type's is `#%% <type>`
ESCAPED = '#%%'  # read_file puts a `#` before a source line starting so
# the lead's reading calls, besides a Bash command that only reads: each counts toward the research note
READING_TOOLS = (
    'Read',
    PYCHARM_READ,
    'mcp__pycharm__search_text',
    'mcp__pycharm__search_regex',
    'mcp__pycharm__search_file',
    'mcp__pycharm__search_symbol',
    'mcp__pycharm__get_symbol_info',
    'mcp__pycharm__analyze_calls',
    'mcp__pycharm__list_directory_tree',
    # Claude Code gives them to a session with Bash on Windows, not on macOS, Linux or WSL (its tools reference, Glob
    # tool behavior)
    'Grep',
    'Glob',
)
# what a Bash call that only reads runs (the module docstring)
READERS = frozenset(('grep', 'find', 'ls', 'cat', 'head', 'tail', 'sed', 'wc', 'sort', 'uniq', 'cut', 'diff', 'jq'))
GIT_READS = frozenset(('log', 'show', 'diff', 'blame', 'grep', 'ls-files', 'status'))
PYTHONS = ('python3', 'mcp_server/venv/bin/python')
LOOKUP = 'scripts/review_lookup.py'  # run with a finding's ID, it prints the finding
DISCARDED = re.compile(r'[12&]?>\s*/dev/null|[12]>&[12]')  # the redirections that write no file
RESEARCH_READS = 8  # the lead's reading calls of one turn that get the research note, and each 8 more
RESEARCH_NOTE = (
    "%d reading calls this turn (Read, Grep, Glob, PyCharm's reads, searches and lookups, Bash commands that only "
    'read). If this is research, hand the rest to the `analyst` agent (AGENTS.md, Delegating to subagents).'
)
STATE_FOLDER = ''  # where each session's count of reading calls is kept: the system's temporary folder when empty
WEB = ('WebFetch', 'WebSearch')  # the lead's are refused: they go to the analyst (the user, 2026-11-19)
PYCHARM_NUMBER = 'L%d: '  # what read_file puts before each line
PYCHARM_CUT = '…%d lines truncated…\n'  # the line read_file shows for the lines it cut from the middle
PYCHARM_LIMIT = 2000  # the lines read_file shows without `limit`
PYCHARM_MAX = 5000  # the largest `limit` read_file takes


class Returned(NamedTuple):
    """What a read returns of a file."""

    size: int  # bytes, the line numbers included
    lines: int  # the file's lines, not read_file's line saying how many it cut
    # False when the hook stopped once it knew whether the read passes READ_LIMIT: size is then a bound, the lower one
    # of a read over it, and lines are those it read
    whole: bool = True


def read_refusal(call: object) -> str | None:
    """Why the lead's read of a big file is refused, whole or ranged, or None to let the read through."""
    fields = _leads(call)
    tool_input = _object(fields, 'tool_input')
    file_path = _text(tool_input, 'file_path')
    pycharm = fields.get('tool_name') == PYCHARM_READ
    if pycharm:
        named = file_path.removeprefix(FILE_URL)
        if named != file_path and not os.path.isabs(named):  # `file://localhost/x` or `file://x`: no file
            return None
        path = _path(_text(tool_input, 'projectPath') or PROJECT, named)
    else:
        named, path = file_path, _path(_text(fields, 'cwd'), _home(file_path))
    suffix = _suffix(path)
    unmeasured = suffix in UNMEASURED or (suffix == NOTEBOOK and not pycharm)
    if any(mark in named for mark in NOT_PATHS) or unmeasured or not os.path.isabs(path):
        return None
    try:
        found = os.stat(path)
    except (OSError, ValueError):  # missing or unreachable, or a NUL in the path
        return None
    if not stat.S_ISREG(found.st_mode) or _is_plan(path):
        return None
    returned = _returned(path, pycharm, tool_input.get('offset'), tool_input.get('limit'))
    if returned is None or returned.size <= READ_LIMIT:
        return None
    # read_file's limit keeps the start and the end of what follows offset (the module's docstring), so a range goes
    # to Read, which finds a relative path from its cwd: the file is named by the path the hook measured. Read shows a
    # notebook's cells unsized, so a notebook's range stays with read_file. Read's notebooks passed above
    if suffix == NOTEBOOK:
        fewer = (
            "Read fewer lines with `read_file`'s `offset` and a smaller `limit` (the `Read` tool shows a notebook "
            'unsized)'
        )
    elif pycharm:
        fewer = (
            "For a range, use the `Read` tool with `offset` and `limit` (`read_file`'s `limit` keeps the start and the "
            'end of what follows `offset`)'
        )
    else:
        fewer = 'Read fewer lines with `offset` and `limit`'
    return (
        'Blocked: this read returns %s of %s, line numbers included, and a read over %d KB is refused. %s, or ask the '
        '`analyst` agent (AGENTS.md, Delegating to subagents).'
        % (_amount(returned), path if pycharm else file_path, READ_LIMIT // 1000, fewer)
    )


def bash_refusal(call: object) -> str | None:
    """Why the lead's Bash command is refused before it runs: it would print over 20 KB of files. None lets it through,
    as it does a command line the hook can't size, and a call run in the background."""
    fields = _leads(call)
    tool_input = _object(fields, 'tool_input')
    if tool_input.get('run_in_background'):  # its output goes to a file, which the hook sizes when Read reads it
        return None
    printed = _printed(_text(tool_input, 'command'), _text(fields, 'cwd')) or []
    returned = [part for _, part in printed]
    total = Returned(sum(r.size for r in returned), sum(r.lines for r in returned), all(r.whole for r in returned))
    if total.size <= READ_LIMIT:
        return None
    files: dict[str, None] = dict.fromkeys(path for path, _ in printed)
    fewer = (
        'Print fewer lines with `head` or `sed -n` (the Read tool shows a notebook unsized)'
        if any(_suffix(path) == NOTEBOOK for path in files)
        else "Print fewer lines: read them with the Read tool's `offset` and `limit`, or use `head` or `sed -n` on "
        'fewer lines'
    )
    return (
        'Blocked: this command would print %s of %s, and a command printing over %d KB of files is refused. Claude '
        'Code puts an output into your context whole up to a size it sets, and only part of a bigger one. %s. Or ask '
        'the `analyst` agent (AGENTS.md, Delegating to subagents).'
        % (_amount(total), ', '.join(files), READ_LIMIT // 1000, fewer)
    )


def bash_note(call: object) -> str | None:
    """The note on a big Bash output that reached the lead's context, or None. A failed command's output comes in
    `error`, cut to about FAILURE_CUT characters: past that, the note gives its size as "at least"."""
    fields = _leads(call)
    if fields.get('tool_name') != 'Bash':  # a reading call, which the hook only counts
        return None
    failed = fields.get('hook_event_name') == 'PostToolUseFailure'
    response = _object(fields, 'tool_response')
    outputs: tuple[str, ...]
    if failed:
        outputs = (EXIT_CODE.sub('', _text(fields, 'error'), count=1),)
    elif 'persistedOutputPath' in response:  # saved to a file: only a preview reached the context
        return None
    else:
        outputs = (_text(response, 'stdout'), _text(response, 'stderr'))
    size = sum(map(len, outputs))
    if size < OUTPUT_LIMIT:
        return None
    cut = failed and size >= FAILURE_CUT
    lines = sum(len(output.splitlines()) for output in outputs)
    command = ' '.join(_text(_object(fields, 'tool_input'), 'command').split())
    if len(command) > COMMAND_SHOWN:
        command = command[: COMMAND_SHOWN - 3] + '...'
    return (
        'The output of `%s` was %s%s characters and %d lines, and %s reached your context. Give the next command of '
        'that kind to the `analyst` agent, or learn the size of its output first (`git diff --shortstat`, `wc -c`).'
        % (command, 'at least ' if cut else '', format(size, ','), lines, 'it' if cut else 'all of it')
    )


def research_note(call: object) -> str | None:
    """Count the lead's reading call, and return the note on its 8th of a turn, and on each 8th after it. None for any
    other call, and for one it can't count: a payload without `prompt_id`, a `session_id` that isn't a plain name, or a
    count it can't write."""
    fields = _leads(call)
    session, prompt, tool = _text(fields, 'session_id'), _text(fields, 'prompt_id'), fields.get('tool_name')
    if not prompt or not re.fullmatch(r'[\w-]+', session):
        return None
    reading = tool in READING_TOOLS or (tool == 'Bash' and _only_reads(fields))
    if not reading:
        return None
    # here, not above: only a counted call needs it. Its import took about 4 ms, more than half the 7 ms of the hook's
    # other imports, `shlex` then among them (`python -X importtime`, 2026-11-19), in a run of the hook of about 28 ms
    import tempfile

    count = _counted(os.path.join(STATE_FOLDER or tempfile.gettempdir(), 'large_reads_%s.json' % session), prompt)
    return RESEARCH_NOTE % count if count and count % RESEARCH_READS == 0 else None


def _only_reads(fields: dict[str, object]) -> bool:
    """Whether the lead's Bash call `fields` only reads, by the module docstring's approximate test."""
    tool_input = _object(fields, 'tool_input')
    command = _text(tool_input, 'command')
    if tool_input.get('run_in_background') or '$(' in command or '`' in command:
        return False
    import command_lines  # here, not at the top: a hook without it then fails open (command_lines.py's docstring)

    commands = command_lines.commands(DISCARDED.sub(' ', command), command_lines.PIPED)
    return bool(commands and all(_reads(words) for _, words in commands))


def _reads(words: list[str]) -> bool:
    """Whether the simple command `words` runs a program that reads (the module docstring)."""
    program, args = words[0], words[1:]
    if program == 'git':
        while args[:1] == ['-C']:
            args = args[2:]
        return bool(args) and args[0] in GIT_READS
    if program in PYTHONS:
        return args[:1] == [LOOKUP]
    return program in READERS


def _counted(path: str, prompt: str) -> int | None:
    """The reading calls of the prompt `prompt` so far, this one included, or None if the count can't be written. The
    file at `path` holds only the prompt's id and its count: another prompt, or a file cut short, starts from 1."""
    try:
        with open(path, encoding='utf-8') as f:
            held = _dict(json.load(f))
    except (OSError, ValueError):  # no count yet, or a file cut short
        held = {}
    previous = held.get('count') if held.get('prompt_id') == prompt else None
    count = previous + 1 if isinstance(previous, int) else 1
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'prompt_id': prompt, 'count': count}, f)
    except OSError:
        return None
    return count


def web_refusal(call: object) -> str | None:
    """Why the lead's web fetch or search is refused: always, as the user asked (2026-11-19). None for any other call,
    and for a subagent's."""
    if _leads(call).get('tool_name') not in WEB:
        return None
    return (
        "Blocked: the lead's web fetches and searches go to the `analyst` agent, even of one known page: a fetch may "
        'return a whole page, up to 100,000 characters, into your context (the docstring of '
        '`.claude/hooks/large_reads.py`). Ask the `analyst` the question, with the page or the search.'
    )


def _leads(call: object) -> dict[str, object]:
    """The fields of the lead's call, or none for a subagent's call (its payload has `agent_id`) or a malformed one."""
    fields = _dict(call)
    return {} if 'agent_id' in fields else fields


def _object(fields: dict[str, object], key: str) -> dict[str, object]:
    return _dict(fields.get(key))


def _dict(value: object) -> dict[str, object]:
    """`value` if it is a dict, else an empty one: what mypy then checks as a `dict[str, object]`, unlike the
    `dict[Any, Any]` that `isinstance` narrows to."""
    return value if isinstance(value, dict) else {}


def _text(fields: dict[str, object], key: str) -> str:
    value = fields.get(key)
    return value if isinstance(value, str) else ''


def _kb(size: int) -> int:
    """`size` in KB, rounded up: a size over the limit never shows as 20 KB."""
    return math.ceil(size / 1000)


def _home(file_path: str) -> str:
    """`file_path` as Read finds it: without the blanks around it, and with a leading `~/` naming the home folder. Read
    doesn't expand `~user/` (the module docstring)."""
    path = file_path.strip()
    return os.path.expanduser(path) if path.startswith('~/') else path


def _path(cwd: str, file_path: str) -> str:
    """`file_path` joined to `cwd` and read lexically, as Read and PyCharm's `read_file` read it: each `..` drops the
    name before it, a symlink's included, and the trailing separators and `.` parts go (the module docstring). Read
    takes `big.py/` for `big.py` and reads the file (measured 2026-11-18), so the hook measures that file."""
    return os.path.normpath(os.path.join(cwd, file_path))  # an absolute file_path replaces the cwd


def _suffix(path: str) -> str:
    """The extension of the file `path` names, in lower case, as pathlib reads it: `..png` has `.png`, `.png` has
    none."""
    stem, dot, extension = os.path.basename(path).rpartition('.')
    return (dot + extension).lower() if stem and extension else ''


def _sizes(path: str, start: int, stop: int | None) -> Returned:
    """What a command prints of the file at `path`: its lines from `start` to `stop`, as Python slices a list of them,
    0-based, and None for `stop` going to the end. A negative `start` takes the last lines, to the end. In a file over
    BIG, the hook stops once the lines pass READ_LIMIT, and reads the last lines back from the end of the file."""
    with open(path, 'rb', BLOCK) as f:
        big = _big(f)
        if start < 0:  # keeps only the last lines, so a tail of a big log holds no list of all its lines
            return _scan(_last(f, -start) if big else collections.deque(map(len, f), maxlen=-start), big)
        return _scan(itertools.islice(map(len, _lines(f, big)), start, stop), big)


def _number(value: object, default: int) -> int | None:
    """`value` if it is a whole number, `default` if it is None, else None. A bool isn't a number here."""
    if value is None:
        return default
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _big(f: BinaryIO) -> bool:
    """Whether the open file `f` is over BIG. It leaves `f` where it was."""
    here = f.tell()
    big = f.seek(0, os.SEEK_END) > BIG
    f.seek(here)
    return big


def _lines(f: BinaryIO, big: bool) -> Iterator[bytes]:
    """The lines of the open file `f`: the file itself, or in a file over BIG, its lines read up to CAP bytes."""
    return _capped(f) if big else f


def _capped(f: BinaryIO) -> Iterator[bytes]:
    """The lines of the open file `f`, each read up to CAP bytes. The rest of a longer line is read past only when the
    next line is asked for."""
    for line in iter(functools.partial(f.readline, CAP), b''):
        yield line
        while len(line) == CAP and not line.endswith(b'\n'):  # the rest of a line cut at CAP bytes
            line = f.readline(CAP)


def _numbered(lines: Iterable[bytes], size: Callable[[bytes], int] = len) -> Iterator[tuple[int, int]]:
    """The number and `size` of each of a file's `lines`, as both read tools number them: from 1, with an empty line
    after a last newline."""
    number, line = 0, b''
    for number, line in enumerate(lines, 1):
        yield number, size(line)
    if line.endswith(b'\n'):
        yield number + 1, 0


def _scan(sizes: Iterable[int], big: bool) -> Returned:
    """The total of `sizes`, and how many there are. In a file over BIG, it stops once the total passes READ_LIMIT."""
    if not big:
        counted = list(sizes)
        return Returned(sum(counted), len(counted))
    size = lines = 0
    for line in sizes:
        size, lines = size + line, lines + 1
        if size > READ_LIMIT:
            return Returned(size, lines, whole=False)
    return Returned(size, lines)


def _last(f: BinaryIO, count: int, start: int = 0, size: Callable[[bytes], int] = len) -> list[int]:
    """The `size` of each of the last `count` lines of the open file `f` after byte `start`, as Python slices a list of
    them, read back from the end of the file. It stops once what it read back passes READ_LIMIT: its first line may
    then be only the end of a longer one."""
    if count < 1:
        return []
    end = f.seek(0, os.SEEK_END)
    data = b''
    while end > start and data.count(b'\n') <= count and len(data) <= READ_LIMIT:
        step = min(BLOCK, end - start)
        end -= step
        f.seek(end)
        data = f.read(step) + data
    return [size(line) for line in io.BytesIO(data).readlines()[-count:]]


def _has_line(f: BinaryIO, number: int) -> bool:
    """Whether the open file `f`, which isn't empty, has a line `number` (1-based), as `_numbered` counts them: one
    line more than it has newlines. It counts the newlines from the start of the file only until there are enough, and
    leaves `f` where it was."""
    here, newlines = f.tell(), 0
    f.seek(0)
    while newlines < number - 1 and (data := f.read(BLOCK)):
        newlines += data.count(b'\n')
    f.seek(here)
    return newlines >= number - 1


def _returned(path: str, pycharm: bool, offset: object, limit: object) -> Returned | None:
    """What a read of the regular file at `path` returns: PyCharm's read_file if `pycharm`, of a notebook's text
    included, else Read. None for a read the hook can't size."""
    if pycharm and _suffix(path) == NOTEBOOK:
        text = _notebook(path)
        return None if text is None else _pycharm_returns(io.BytesIO(text), offset, limit)
    with open(path, 'rb', BLOCK) as f:
        if pycharm:
            return _pycharm_returns(io.BufferedReader(_PyCharmLines(f), BLOCK), offset, limit)
        return _read_returns(f, offset, limit)


class _PyCharmLines(io.RawIOBase):
    """The open binary file `f`, with each lone CR read as LF: its lines end where PyCharm's read_file ends them, at LF,
    CRLF or a lone CR. The bytes keep their positions in the file. A CRLF stays as it is, and `_shown` counts it as one
    byte."""

    def __init__(self, f: BinaryIO) -> None:
        super().__init__()
        self.f = f

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def seek(self, offset: int, whence: int = os.SEEK_SET, /) -> int:
        return self.f.seek(offset, whence)

    def tell(self) -> int:
        return self.f.tell()

    def readinto(self, buffer: Buffer, /) -> int:
        view = memoryview(buffer)
        data = self.f.read(len(view))
        if b'\r' in data:  # the byte after `data` tells whether a CR ending it is a lone one: read, then given back
            after = self.f.read(1)
            self.f.seek(-len(after), os.SEEK_CUR)
            data = LONE_CR.sub(b'\n', data + after)[: len(data)]
        view[: len(data)] = data
        return len(data)


def _shown(line: bytes) -> int:
    """The bytes PyCharm's read_file shows of a line of `_PyCharmLines`, counting a CRLF ending it as one."""
    return len(line) - line.endswith(b'\r\n')


def _read_returns(f: BinaryIO, offset: object, limit: object) -> Returned | None:
    """What Read returns of the open file `f`, or None for a value that isn't a whole number. Read returns `limit`
    lines from line `offset` (1-based): from the first line for an `offset` of 0 or less, and to the end for a `limit`
    of 0 or less. Each line comes after its number and a tab (READ_NUMBER). In a file over BIG, the hook stops once
    the read passes READ_LIMIT."""
    first, count = _number(offset, 1), _number(limit, 0)
    if first is None or count is None:
        return None
    big, start = _big(f), max(first, 1) - 1
    shown = itertools.islice(_numbered(_lines(f, big)), start, start + count if count > 0 else None)
    return _scan((line + len(READ_NUMBER % number) for number, line in shown), big)


def _pycharm_returns(f: BinaryIO, offset: object, limit: object) -> Returned | None:
    """What PyCharm's read_file returns of the open file `f`, or None for a call it answers with an error: an `offset`
    under 1 or past the last line, or a `limit` out of range. It returns the lines from line `offset` (1-based) to the
    end, each after `L<n>: `. Past `limit` lines it keeps the first half
    of `limit` and the rest from the end, with a line saying how many it cut. In a file over BIG, the hook stops once
    the first half passes READ_LIMIT, and reads the lines between the halves only when `_bounded` can't tell."""
    first, count = _number(offset, 1), _number(limit, PYCHARM_LIMIT)
    if first is None or count is None or first < 1 or not 1 <= count <= PYCHARM_MAX:
        return None
    big, half = _big(f), count // 2
    shown = itertools.islice(_numbered(_lines(f, big), _shown), first - 1, None)
    head = _scan((line + len(PYCHARM_NUMBER % number) for number, line in itertools.islice(shown, half)), big)
    if not head.whole:
        return head
    # with `limit=1` the head reads no line. Over BIG, `_bounded` then reads the last one back from the end of the file,
    # and nothing has checked that line `first` is in it (REVIEW.md AGT-108)
    if big and not half and not _has_line(f, first):
        return None
    bounded = _bounded(f, head, first, count - half) if big and head.lines == half else None  # lines follow the head
    if bounded is not None:
        return bounded
    tail = collections.deque(shown, maxlen=count - half)  # the lines after the head, or the last of them
    if not head.lines and not tail:  # no line `first`: read_file answers an offset past the last line with an error
        return None
    cut = tail[0][0] - first - head.lines if tail else 0  # the lines are numbered on from `first`
    size = (
        head.size
        + sum(line + len(PYCHARM_NUMBER % number) for number, line in tail)
        + (len((PYCHARM_CUT % cut).encode()) if cut else 0)
    )
    return Returned(size, head.lines + len(tail), not big or all(line < CAP for _, line in tail))


def _bounded(f: BinaryIO, head: Returned, first: int, count: int) -> Returned | None:
    """Bounds of what read_file returns of the open file `f`, over BIG, when they tell whether it passes READ_LIMIT:
    the lower one when it does, the upper one when it doesn't. None when they can't tell. `head` is the first half
    read_file shows, from line `first`, and `count` the lines it shows from the end of the file, which the hook reads
    back from there. None too when `head` read the file to its end: the lines left, at most the empty one after a last
    newline, are then counted exactly. `f` is left after `head`."""
    after, end = f.tell(), f.seek(-1, os.SEEK_END)
    if after > end:  # the head may hold the empty line after a last newline, which `empty` would count again
        f.seek(after)
        return None
    empty = f.read(1) == b'\n'  # read_file shows an empty line after a last newline, as the last of them
    last = _last(f, count - empty, after, _shown)
    f.seek(after)
    size, shown = head.size + sum(last), len(last) + empty
    # their numbers come after the head's, and are at most the file's bytes and one, as the lines cut are
    lower = size + shown * len(PYCHARM_NUMBER % (first + head.lines))
    upper = size + shown * len(PYCHARM_NUMBER % (end + 2)) + len((PYCHARM_CUT % (end + 2)).encode())
    if lower > READ_LIMIT or upper <= READ_LIMIT:
        return Returned(lower if lower > READ_LIMIT else upper, head.lines + shown, whole=False)
    return None


def _amount(returned: Returned) -> str:
    """How much a refused read or command returns: its size and lines, or only that it passes READ_LIMIT where the
    hook stopped there."""
    if returned.whole:
        return '%d KB and %d lines' % (_kb(returned.size), returned.lines)
    return 'over %d KB' % (READ_LIMIT // 1000)


def _notebook(path: str) -> bytes | None:
    """The text PyCharm's read_file shows of the notebook at `path`, in UTF-8 (the module docstring). None for a
    notebook the hook can't rebuild: one it can't parse, or a cell without a type or a source of text."""
    try:
        with open(path, encoding='utf-8') as f:
            cells = _list(_dict(json.load(f)).get('cells'))
    except (OSError, ValueError):  # unreadable, or not JSON
        return None
    if cells is None:
        return None
    shown = []
    for cell in map(_dict, cells):
        kind, source = _text(cell, 'cell_type'), _source(cell.get('source'))
        if not kind or source is None:
            return None
        lines = source.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        escaped = ('#' + line if line.startswith(ESCAPED) else line for line in lines)
        shown.append('\n'.join((CELL_MARKERS.get(kind, '#%% ' + kind), *escaped)))
    return '\n'.join(shown).encode()


def _source(value: object) -> str | None:
    """A notebook cell's source as text: a string, or a list of strings joined. None for anything else."""
    if isinstance(value, str):
        return value
    parts = _list(value)
    if parts is None:
        return None
    texts = [part for part in parts if isinstance(part, str)]
    return ''.join(texts) if len(texts) == len(parts) else None


def _list(value: object) -> list[object] | None:
    """`value` if it is a list, else None: a `list[object]` for mypy, unlike the `list[Any]` that `isinstance` narrows
    to."""
    return value if isinstance(value, list) else None


def _printed(command: str, cwd: str) -> list[tuple[str, Returned]] | None:
    """The real path of each file the commands of `command` print, with what they print of it (`_sizes`), up to a
    command of MOVES that the hook doesn't follow. None for a command line the hook can't size. A refused command's
    `cd` never ran, so the refusal names each file by that path, which Read finds from any folder. A program opens a
    `..` after a symlink physically, while Read reads it lexically, so only the real path is the file the program
    prints for Read too (REVIEW.md AGT-95)."""
    import command_lines  # here, not at the top: a hook without it then fails open (command_lines.py's docstring)

    spans = command_lines.spans(command, cwd)
    if spans is None or not all(os.path.isfile(path) for path, _, _ in spans):  # a missing file, or not a regular one
        return None
    printed = []
    for path, start, stop in spans:
        real = os.path.realpath(path)
        printed.append((real, _sizes(real, start, stop)))
    return printed


def _is_plan(path: str) -> bool:
    try:
        return os.path.samefile(path, PLAN)
    except OSError:  # no PLAN.md: a branch's plan is deleted as it merges
        return False


def _answer(call: object) -> int:
    """Answer the call: exit 2 with the reason on stderr to refuse a read or a command, else exit 0. After a call that
    succeeded or failed, the notes on a big Bash output and on the turn's reading calls go on stdout as JSON."""
    fields = _leads(call)
    event = fields.get('hook_event_name')
    if event == 'PreToolUse':
        tool = fields.get('tool_name')
        reason = (web_refusal if tool in WEB else bash_refusal if tool == 'Bash' else read_refusal)(call)
        if reason:
            print(reason, file=sys.stderr)
            return 2
    elif event in ('PostToolUse', 'PostToolUseFailure'):
        notes = [note for note in (bash_note(call), research_note(call)) if note]
        if notes:
            context = '\n\n'.join(notes)
            print(json.dumps({'hookSpecificOutput': {'hookEventName': event, 'additionalContext': context}}))
    return 0


def main() -> int:
    try:
        return _answer(json.load(sys.stdin))
    except Exception:  # fail open: a broken hook must not block the lead's reads
        return 0


if __name__ == '__main__':
    sys.exit(main())
