# REVIEW.md: review findings

Findings from code reviews of this repository, kept across several reviews as a file in the project. How many is
the user's choice, most likely the life of a feature branch; the history stays in git for good.

This file is the **memory per branch**. Agents that review and agents that address findings talk through it, as
in a PR review: a finding is raised, then fixed or answered with why not, so the next reviewers know what was
settled and don't raise it again. Once the branch is merged it can be cleaned up. `DECISIONS.md` is the memory for
the whole project.

A new review **appends** its findings to the matching severity section and adds itself to the log; it never removes
or rewrites existing entries. An entry is checked when it is resolved, always with a resolution line that starts
with one of these wordings: done, not a bug, not reproducible, won't fix. Format and rules:
`.claude/skills/project-code-review/` (SKILL.md, TEMPLATE.md).

**Confidence.**

- *Confirmed*: the lead agent read the code and the defect is visible in it, as quoted.
- *Measured*: reading couldn't settle it, and the lead agent's scratch probe in Designer showed it (the entry gives
  the probe and what it measured; the `project-code-review` skill). A finding is one or the other, never a guess.

**IDs.** One prefix per area, numbered on: **PLG** plugin and bridge protocol, **SRV**
`mcp_server/server.py`, `server_tools/` and `designer_preferences.py`, **HLP** `mcp_server/designer_helpers/`, **INS** installer, uninstaller,
command-line client, example and `scripts/`, **TST** tests and docs. A new area gets a new prefix, added here.

**Last used:** PLG-45, SRV-174, HLP-185, INS-41, TST-500.

A new finding takes the next number for its area, and whoever writes it updates this line in the same edit. Only a
new finding raises it, and a cleanup leaves it as it is. Nothing lowers a committed number; dropping a finding before
committing it undoes its change.

**Findings no longer here.** Only the user starts a cleanup of this file (the `cleanup-review` skill). An ID
cited elsewhere but missing here was usually removed by one, which isn't a dangling reference.
`python3 scripts/review_lookup.py HLP-56` prints the whole entry, from this file or its git history, from any folder
of the repo. If it can't, it says why: the ID never existed, a squash lost it, or the clone is shallow.

## Status

| Severity | Open | Resolved |
|---|---|---|
| High | 0 | 0 |
| Medium-high | 0 | 0 |
| Medium | 0 | 0 |
| Low-medium | 0 | 0 |
| Low | 0 | 5 |
| **Total** | **0** | **5** |

## Review log

### 2026-11-17: the disallow-any-explicit branch against main (ROADMAP item 99), the diff only

- **How:** two reviewer subagents, no tests run. One took `mypy.ini`, `tests/unit/test_types.py`, AGENTS.md and
  ROADMAP.md. The other took the 54 removed `# type: ignore[no-untyped-call]` comments in 50 files, and what still
  refers to them. The lead agent read each suspicion. Three needed a scratch probe outside Designer: mypy 2.4.1 run with
  the repository's `mypy.ini` on small files in the scratchpad. It measured the mark's place in a signature spanning
  several lines (TST-496), the `Any` inside an expression (TST-497), and `FORCE_COLOR=1` (TST-499). No suspicion was
  settled as wrong.
- **Not verified:** none.
- **Resolutions assessed:** none in scope. REVIEW.md had no entries after its cleanup.
- **Findings:** TST-496 to TST-500, all Low. Both reviewers found TST-498, merged into one entry.
- **Suggested order:** TST-497 and TST-496 first, since they change what AGENTS.md tells agents and reviewers to do.
  Then TST-498 and TST-499 in the test, then TST-500's wording.
- **Checked and found fine:**
  - The new test fails with `disallow_any_explicit` off.
  - Output the test can't parse fails it rather than passing it: a crash, column numbers, a syntax error.
  - The test reads Windows paths and CRLF line endings.
  - `_mypy` keeps what the two whole-repo runs checked: cwd, env with `MYPYPATH`, cache dir, argument order, and the
    message when mypy isn't installed.
  - A file named on the command line replaces `mypy.ini`'s `files`. The sd, PySide6 and shiboken6 section keeps their
    own code quiet. Without Designer, sd's names are an implicit `Any`, never an explicit one.
  - The three `untyped_calls_exclude` names match their definitions in Designer's sd package. mypy matches a name
    exactly or by dotted prefix, so they let no other function through. No other unannotated sd function is called in
    checked code.
  - The removed ignores left no dead cast, annotated local or import. Every remaining cast still has its explanation.
  - Nothing still refers to the removed ignores or to the old `# Any:` mark. The remaining sd ignores (`union-attr`,
    `attr-defined`) still justify `--no-warn-unused-ignores` in the run without Designer.

---

## High

## Medium-high

## Medium

## Low-medium

## Low

- [x] **TST-496 · AGENTS.md puts the mark on the `Any`'s line; for a signature spanning several lines mypy wants it on the `def` line** · `AGENTS.md:160` · measured · found 2026-11-17
  - **Defect.** AGENTS.md says an `Any` that stays is "marked as an exception with its reason on the same line:
    `# type: ignore[explicit-any]  # <reason>`". mypy reports a function's explicit `Any` on its `def` line, and an
    ignore covers only the line it is on. When ruff splits a signature over several lines, the mark on the parameter's
    line doesn't silence the error.
  - **Scenario.** The probe ran mypy with `mypy.ini` on `def f(\n    x: Any,  # type: ignore[explicit-any]\n) -> None:
    ...`. It reported `4: Explicit "Any" is not allowed [explicit-any]` on the `def` line and
    `5: Unused "type: ignore" comment [unused-ignore]` on the parameter's line. The same mark on the `def` line drew no
    error. An agent following AGENTS.md gets two errors it can't explain, and a wasted round.
  - **Fix.** AGENTS.md says the mark goes on the line mypy reports, which for a function is its `def` line. The test's
    probe gets a function on several lines with the mark on its `def` line, expecting no error.
  - **Resolution: done.**
    - **Test:** the probe in `test_mypy_refuses_an_explicit_any` (`tests/unit/test_types.py`) gets `def i(` over three
      lines, with the mark on its `def` line, and expects no error. The defect was AGENTS.md's wording, so this line
      passed before the fix too. It backs the new sentence.
    - **Cause:** AGENTS.md placed the mark by the `Any`. mypy reports a function's explicit `Any` on its `def` line, and
      an ignore covers only its own line.
    - **Fix:** AGENTS.md says the mark goes on the line mypy reports. For a function, that is its `def` line, even when
      the signature spans several lines.
    - **Also covered:** searched the docs, skills and Python for "reason on", "on its line" and "same line". The
      `project-code-review` skill said an `Any` is marked "with its reason on its line". It now says "with its reason,
      as those rules say", leaving the place to AGENTS.md.

- [x] **TST-497 · The new sentences say mypy reports every `Any` written out; it misses one written inside an expression** · `AGENTS.md:161`, `mypy.ini:14`, `tests/unit/test_types.py:105`, `ROADMAP.md:88` · measured · found 2026-11-17
  - **Defect.** AGENTS.md says "mypy refuses every `Any` written out without the mark". mypy.ini's comment, the new
    test's docstring and ROADMAP item 99's text say mypy reports every `Any` written out. mypy checks annotations,
    signatures, casts and aliases. It doesn't check an `Any` in a type used as a value in an expression.
  - **Scenario.** The probe ran mypy with `mypy.ini` on `a = defaultdict[str, Any](int)`, `take(dict[str, Any])`,
    `c = list[Any]()` and `b: object = Any`. It found no issue. AGENTS.md tells reviewers to look only for an `Any`
    that comes in implicitly, so one trusting it misses these.
  - **Fix.** The sentences name where mypy looks (an annotation, a signature, a `cast`, an alias) instead of "every".
    AGENTS.md also names the gap: an `Any` inside an expression, such as `defaultdict[str, Any](int)`, isn't reported,
    so look for those too. The test's probe gets that line, expecting no error, so the sentence has its check.
  - **Resolution: done.**
    - **Test:** the probe in `test_mypy_refuses_an_explicit_any` gets `g = defaultdict[str, Any](int)` and expects no
      error on it. The defect was in the sentences, not in mypy.ini, so this line passed before the fix too. It backs
      the narrowed sentences. The probe also gets `Pair = tuple[str, Any]` and `def h(x: Any)`, each expected to be
      reported, since the sentences now name type aliases and signatures.
    - **Cause:** the sentences went from the cases measured for ROADMAP item 99 (annotations, casts, aliases) to every
      `Any` written out.
    - **Fix:** AGENTS.md, mypy.ini's comment, the test's docstring and ROADMAP item 99 name where mypy looks: an
      annotation, a signature, a `cast`, a type alias. AGENTS.md, mypy.ini and the docstring name the gap, an `Any`
      inside an expression. AGENTS.md says to look for those too.
    - **Also covered:** searched the docs, skills and Python for "every `Any`" and "every Any". No other place says it.

- [x] **TST-498 · The new test's `errors` is a `set[Any]`, from `re.findall`** · `tests/unit/test_types.py:110` · confirmed · found 2026-11-17
  - **Defect.** `errors = set(re.findall(r'probe\.py:(\d+): error: .*\[([a-z-]+)\]$', ...))`. typeshed gives
    `re.findall` the return type `list[Any]`, so mypy checks nothing about the comparison with `expected`. AGENTS.md
    asks for such an implicit `Any` to be narrowed in a function the branch adds. Both reviewers found it.
  - **Scenario.** A change of the regex to one group makes `errors` a set of `str`. mypy says nothing, and the
    mismatch shows only when the test runs.
  - **Fix.** `errors: set[tuple[str, str]] = set(re.findall(...))`.
  - **Resolution: done.**
    - **Test:** none can fail on it, since mypy doesn't report an implicit `Any` (TST-497). `test_types.py` checks that
      the annotation fits what `re.findall` returns here.
    - **Fix:** `errors: set[tuple[str, str]] = set(re.findall(...))`.
    - **Also covered:** the test's other locals (`probe`, `result`, `expected`) get their types from typed calls, with no
      `Any`. The branch adds no other `re.findall`.

- [x] **TST-499 · The new test fails, with mypy.ini right, when `FORCE_COLOR` or `MYPY_FORCE_COLOR` is set** · `tests/unit/test_types.py:110` · measured · found 2026-11-17
  - **Defect.** The test's regex ends with `\[([a-z-]+)\]$`. With either variable set, mypy colours its output even
    when piped, and each error line ends in a reset escape after the code, so `$` never matches.
  - **Scenario.** The probe ran mypy with `FORCE_COLOR=1`, piped. The line came out as
    `probe_color.py:3: ^[[1m^[[31merror:^[(B^[[m Explicit ... ^[[33m[explicit-any]^[(B^[[m`. The test would then find no
    error, and fail on a correct mypy.ini with a message that points at the config. The same run with
    `--no-color-output` printed plain text. Neither variable is set here today.
  - **Fix.** `_mypy` passes `--no-color-output`.
  - **Resolution: done.**
    - **Test:** `test_mypy_refuses_an_explicit_any` runs mypy with `MYPY_FORCE_COLOR=1`, which mypy reads before
      `FORCE_COLOR`. Without the fix it failed with `assert set() == {('10', 'explicit-any'), ...}`: the regex found no
      error in the coloured lines. The test first ran three times (neither variable, `FORCE_COLOR=1`,
      `MYPY_FORCE_COLOR=1`), and the two forced runs failed this way. The `/simplify` pass kept one forced run, since
      the flag overrides both variables alike, and the run without colour couldn't fail on it.
    - **Cause:** mypy colours its output when either variable is set, even into a pipe. The reset escape after each
      error code kept the test's `$` from matching.
    - **Fix:** `_mypy` passes `--no-color-output`, for every run in `test_types.py`.
    - **Also covered:** the other tests that read a tool's output. `test_lifecycle_env.py`'s mypy run asserts
      `'kqueue' not in result.stdout`. Colour wraps a quoted name in escapes without splitting it (the review's probe
      printed `^[[1m"Any"^[(B^[[m`), so that check can't pass falsely. `test_lint.py`'s ruff runs check only the exit
      code.

- [x] **TST-500 · mypy.ini and ROADMAP item 99 say every Designer script calls the three excluded sd functions first** · `mypy.ini:17`, `ROADMAP.md:88` · confirmed · found 2026-11-17
  - **Defect.** mypy.ini says "The sd functions that every Designer script calls first", and ROADMAP item 99's Done
    text says the same. `sd.getContext()` is called in about 60 checked files, but `getQtForPythonUIMgr()` in only 6:
    `core.py` and five Designer scripts.
  - **Scenario.** A maintainer meets another unannotated sd function, such as `ctx.getLogger()`. The comment's rule,
    "every script calls them first", doesn't say whether that one belongs in the list or takes an ignore.
  - **Fix.** Say what the list holds: the sd functions that scripts call to reach the application and its Qt UI
    manager.
  - **Resolution: done.**
    - **Fix:** mypy.ini and ROADMAP item 99 say the list holds the sd functions that Designer scripts call to reach the
      application and its Qt UI manager.
    - **Also covered:** searched for "every Designer script". No other place says it.
