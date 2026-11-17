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

**Last used:** PLG-45, SRV-174, HLP-185, INS-41, TST-495.

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
| Low-medium | 0 | 1 |
| Low | 0 | 26 |
| **Total** | **0** | **27** |

## Review log

### 2026-11-17: the narrower-types branch against main (ROADMAP item 98), the diff only

- **How:** five reviewers, one area each of `git diff main...narrower-types` at 70f8e71:
  - the helpers;
  - the server, plugin, client, installers, scripts, example and docs;
  - the self-test;
  - the unit tests, in two parts.

  They ran no tests and sent nothing to Designer; two ran plain-Python or mypy checks of language behaviour on
  scratch files. Four /simplify reviewers read the same diff at the same time; their cleanups are below. The lead
  agent settled every suspicion by reading the code, and probed one in a Designer it started.
  - **Probe:** an output node's `usages`, read fresh and after being set to an empty `SDValueArray`, gave an
    `SDValueArray` whose `.get()` is an empty array both times, never None.
  - **Settled as wrong:**
    - `_usage_names` dropping main's `array is not None` guard. The probe found no case where it matters, and
      `tags is None` is still handled.
    - `JsonSent` admitting `bytes`. Its comment says "any sequence or mapping of them", which bytes is, so it doesn't
      mislead.
    - `selftest_fakes.py`'s docstring. It was incomplete, not false, already on main.
    - The commit's ROADMAP items 102 and 103. They were in the tree before this session, and are a question for the
      user, not a finding.
- **Not verified:** none.
- **Resolutions assessed:** none in scope: the file held no entries after its cleanup. The DECISIONS.md entries
  whose code the diff touches still hold, and none was raised again.
- **Findings:** HLP-182 to HLP-184, SRV-172 and SRV-173, INS-40, TST-480 to TST-488: 1 Low-medium and 14 Low. Two
  reviewers found HLP-182, and two found SRV-172. No chain: every finding is generation 1.
- **Suggested order:** HLP-182 first: the helpers keep a job's scope alive in Designer. Then the other product code:
  SRV-173, INS-40, SRV-172, HLP-183 and HLP-184. Then the tests and docs: TST-480 to TST-488.
- **Simplifications:** a third /simplify pass, applied in this change, with the unit tests of the code it touches
  passing before and after (1525) and every tool's schema unchanged:
  - one pinned schema pair (`JsonObject`, `AnyJson`, server_tools/core.py) for the three tools' JSON parameters;
  - `fake_bridge` for 15 more bridge fakes that read only `code`;
  - `tool_result` and `code_of` in selftest_fakes.py for 13 result stand-ins and 5 casts, and one `_bridge_error`;
  - `selftest_fakes.fresh` for 5 module loaders;
  - `read_agent_record` and `Greeting` where tests parsed by hand, and one `FakeGraph` in conftest.py;
  - the accessors `_menu`, `_ui_mgr` and `_value` (designer_helpers/core.py) for 10 casts;
  - the helpers' own `_Counts`, `_Frames` and `_Screen` for 4 Protocols that restated them in tests;
  - `_not_finite`'s needless local, 3 unused re-export markers, a typed local and 3 local imports.

  Skipped:
  - the `@overload`s and `_agent_home`: HLP-182 and SRV-172;
  - `SkipValidation` on the JSON parameters: about 0.1 ms per call, and the validation is kept;
  - iterating `getNodes()` by index: the unit tests' fakes return lists;
  - EditOp defined inside `apply_edits`: about 36 µs per call, against the batch's types in one place;
  - `ToolArgs` for `dict[str, Json]`: the narrower type stays;
  - guards for view3d's casts: the casts fail loudly on purpose;
  - `_Ended` as `WorkerEnd`: a test reads `'quit_at' in ENDED`;
  - hoisting `remove_graph_input`'s type read: it would also run with no bound parameter;
  - helpers for `_xy` pairs: marginal.

  Proposed for ROADMAP.md: the plugin caching the compiled helpers, about 24 ms of every call; and, with item 99,
  `untyped_calls_exclude` in mypy.ini for sd's three untyped functions, which would remove 54 ignores.
  Note (2026-11-17): the user declined the compile cache, so it isn't in ROADMAP.md.
- **Checked and found fine:**
  - **Helpers:** every name evaluated as the parts load is bound before it is used, and no part rebinds another's.
    The accessors make the calls they replace. `_default_output`, `_target` and the view3d casts fail as main's
    code did.
  - **Server:** the tools' JSON parameters validate parsed JSON as before, inf and nan included. The bridge protocol
    is unchanged on the wire. `review_lookup`'s `args.finding is not None` matches `not args.last_used`.
  - **The plugin and the 3.9 scripts:** the plugin's annotations evaluate on Designer's 3.13, and the 3.9 scripts'
    TypedDicts and Protocols work there.
  - **Self-test:** the five rewritten `check` conditions give the same truth values. The TypeGuards test what the
    old isinstance tests did. Every Designer script makes the same calls in the same order.
  - **Unit tests:**
    - every `fake_bridge` conversion read only `code`;
    - the `_popen(..., processes=)` fakes keep their order;
    - `_started_with` is cleared before and after every test;
    - only three assertion lines changed, all equivalent.

### 2026-11-17: the narrower-types branch again, what changed since the first review (70f8e71)

- **How:** two reviewers read `git diff 70f8e71` and the new `editor_panels_and_fit/printed.py`:
  - one the product code and the docs;
  - one the unit tests and the live self-test.

  The diff holds the third /simplify pass, the fixes of HLP-182 to TST-488, and ROADMAP items 99 and 105. Each
  reviewer judged the resolutions in its area on its own, as the agent that wrote them led the review. They ran no
  tests and sent nothing to Designer, apart from the product reviewer's inline mypy checks of language behaviour. The
  lead agent settled every suspicion by reading, and one with a plain-Python probe: mypy strict, on a scratch file, took
  a `__code__` Protocol unioned with `type` for functions and classes (TST-493). The second reviewer's `_points_here`
  finding and the first's were one: TST-490.
- **Not verified:** none.
- **Resolutions assessed:** all 15 of HLP-182 to TST-488. Each fix addresses the cause it names, and each test that
  names a failure fails without its fix. Questioned:
  - HLP-182 by PLG-44: the cause is in the plugin's job model too;
  - SRV-172 by SRV-174: a second double read, in log.py;
  - HLP-183 by HLP-185: the reworded comments still say more;
  - SRV-173 by INS-41 (a type, and the resolution's wording) and TST-490 (the parts with no test);
  - TST-480 by TST-489: more fakes typed against values they never get;
  - TST-484 by TST-491: a comment kept the old name;
  - INS-40 by TST-492: a docstring kept "older than 3.10".
- **Findings:** PLG-44, SRV-174, HLP-185, INS-41, TST-489 to TST-495: 11 Low. The longest chains are at generation 2
  (eight of them); none is at generation 3.
- **Suggested order:** PLG-44 and SRV-174, in the plugin and the server; then HLP-185, INS-41 and TST-490; then the
  rest, all tests or docs.
- **Checked and found fine:**
  - **HLP-182:** the five casts replace the overloads one for one. No other typing call in code run as a job stores
    an object globally: `Union`, `Literal` and `TypeGuard` were checked. The unit test and the live check fail on the
    old code, and the live check can't pass on `HELD` or `NO_REF`.
  - **The third /simplify pass:**
    - `_menu`, `_ui_mgr` and `_value` make the calls and casts they replaced, at all 10 sites.
    - `fresh()`, `tool_result`, `code_of` and every `fake_bridge` conversion do what the code they replaced did.
    - The helpers' real `_Counts`, `_Frames` and `_Screen` are imported for the checker only.
    - No assertion was dropped or loosened.
  - **The other resolutions:**
    - SRV-172's and TST-485's tests fail on the old code; `_PINNED` equals main's schemas.
    - HLP-184's `_input_read` changes nothing for the string a get node holds.
    - TST-481's and TST-482's changes check what they say.
  - **Docs:** TST-486's and TST-487's wording matches the plugin and `read_agent_record`. Item 99's figures hold: 54
    ignores, all on the three sd functions. Item 104 says 744.

---

## High

## Medium-high

## Medium

## Low-medium

- [x] **HLP-182 · `_send`'s `@overload` stubs keep each helpers job's scope alive after the job** · `mcp_server/designer_helpers/mac_window.py:47-66` · confirmed · found 2026-11-17
  - **Defect.** `typing.overload` stores each stub in `typing._overload_registry[module][qualname][first line]`
    (Python 3.11 and later). The helpers run as `__main__` in the plugin's job scope, so the four stubs of
    `_MacWindow._send` land under the same key at every helpers job. Each stub's `__globals__` is its job's scope, so
    the last helpers job's scope stays alive until the next one replaces the stubs, or until Python ends. On main
    nothing referenced the scope after its job, and it was freed at once.
  - **Scenario.** A tool runs the helpers, then Designer idles or quits. The job's scope stays alive with everything
    at the helpers' module level: `_APP` and `_PM`, sd objects whose `__del__` calls into Designer; the plugin's
    `_after_reply`; and any object an `execute_designer_code` script made after prepending the helpers, such as a
    texture or a Qt wrapper. Kept until Python ends, they are released during Designer's shutdown (DECISIONS.md treats
    objects kept that long as a risk at quit: the plugin's timer and waker). A reviewer measured it in plain Python
    3.12, with a scope like the plugin's: a sentinel of the first job was still alive after `gc.collect()`, and was
    freed only by the next job; without the overloads, at once. About 530 KB stays alive between calls. Found by two
    reviewers (one as a cleanup).
  - **Fix.** Drop the overloads: keep `_send -> bool | int | float | None` and cast at the five call sites, as main
    did (`_object`, `_items`, `covered`, `number`, `appearance`), or put typed methods (`_send_pointer`,
    `_send_integer`, `_send_double`) over one untyped `_send`. Drop core.py's `overload` re-export if nothing else
    uses it. A unit test: once the helpers' text has run in a fresh `__main__` scope, nothing of it is left in
    `typing._overload_registry`, or the scope is collected once dropped.
  - **Resolution: done.**
    - **Test:** `test_a_job_running_the_helpers_leaves_its_scope_to_be_freed` (tests/unit/test_designer_helpers.py)
      runs the helpers' text in a scope like the plugin's, drops it, and checks that an object only it held was freed.
      It failed: "the job ended, its scope still held". The live check
      `check_a_helpers_job_leaves_its_scope_to_be_freed` (bridge) does the same across two jobs in Designer. In its
      scratch run it failed with `HELD`.
    - **Cause:** `typing.overload` keeps every stub it decorates, keyed by module, name and line. The helpers run as
      `__main__`, so the four stubs of `_MacWindow._send` kept the last job's scope, their globals, alive.
    - **Fix:** `_send` has no `@overload`s. It returns `bool | int | float | None`, and its five callers cast the
      result to the type their `result` gives, as main did. Its docstring says why. core.py no longer re-exports
      `overload`.
    - **Also covered:** every Python file searched for `overload`. No other code that runs as a job (the plugin's
      jobs, `examples/`, the self-test's Designer scripts) uses it.
  - Questioned by PLG-44 (2026-11-17).

## Low

- [x] **HLP-183 · Two new comments say the conversions refuse more than they do** · `mcp_server/designer_helpers/batch.py:45-48`, `mcp_server/designer_helpers/edits.py:65-66` · confirmed · found 2026-11-17
  - **Defect.** EditOp's comment: "A value of another type fails when its op runs, unless the op converts it (a node
    id, a position's numbers)". `_make_value`'s docstring: "A builder's conversion refuses a value it can't convert
    (TypeError, ValueError)".
  - **Scenario.** An expose op's `label`, `min`, `max`, `step` and `group` are stored whatever their JSON type:
    `_set_annotation` stores a number as a float annotation and anything else as text, so `'min': '0'` becomes a text
    annotation, with no failure. A set op's `string` parameter takes any value through `str()`. `as_bool('maybe')`
    and `as_int(2.5)` raise RuntimeError, not TypeError or ValueError. A reader trusting either comment expects a
    refusal that doesn't come.
  - **Fix.** Name what converts: a node id, a position's numbers, a parameter's value (`_make_value`), and an
    exposed input's annotations (`_set_annotation`, which stores a non-number as text). In `_make_value`'s docstring,
    say that the builders' own checks raise RuntimeError, and `float()` and `int()` TypeError or ValueError.
  - **Resolution: done.**
    - **Test:** none: comments only.
    - **Fix:** EditOp's comment names what converts a value (a node id, a position's numbers, a parameter's value).
      It also says how an exposed input's annotations are stored: a bool as a bool, a number as a float, anything
      else as text. `_make_value`'s docstring says `as_bool` and `as_int` refuse with RuntimeError, `float()` and
      `int()` with TypeError or ValueError, and that a string parameter takes any value.
  - Questioned by HLP-185 (2026-11-17).

- [x] **HLP-184 · `_plain_binding` and `_input_users` type input ids as `Shown`, where they are `str | None`** · `mcp_server/designer_helpers/graph_inputs.py:220`, `:327` · confirmed · found 2026-11-17
  - **Defect.** `_plain_binding -> Shown` and `_input_users -> dict[Shown, list[str]]`. The ids are `fmt()` of a get
    node's `__constant__`, an SDValueString, which gives a str (`'<SDValueString>'` when `.get()` raises) or None,
    and `_graph_parameter_reads`' XML `get('v')`, a `str | None`. `Shown` adds bools, numbers and tuples that never
    occur.
  - **Scenario.** None at run time: the callers convert with `str(source)`. A caller comparing a key with a number
    type-checks.
  - **Fix.** Type both `str | None`, through a typed accessor such as `_constant(node) -> str | None` that keeps
    `fmt()`'s answer to a `.get()` that raises, used in `_plain_binding` and `_input_users`' `read`.
  - **Resolution: done.**
    - **Test:** mypy strict, which now checks the ids as `str | None`. The existing unit tests of graph_inputs pass,
      and so do the live checks of `inputs` and `params` in the scratch run.
    - **Fix:** `_input_read(get)` gives a get node's `__constant__` as `str | None`. It returns fmt()'s string, and
      None for anything else, which a string value never gives. `_plain_binding` and `_input_users` use it, and are
      typed `str | None`.

- [x] **SRV-172 · `_agent_home` reads the agent record again instead of the bytes `_agent_record` checked** · `mcp_server/server_tools/lifecycle.py:742-748` · confirmed · found 2026-11-17
  - **Defect.** `if _agent_designer(port) is None: return None`, then `seen = _record_bytes(port)`. `_agent_record`
    reads the file, checks the pid and start, and returns `(pid, seen)`; `_agent_designer` drops `seen`, and the home
    comes from a second read of the file. The branch rewrote these lines; main read the file twice too.
  - **Scenario.** Another server's launch on the same port replaces the record between the two reads: the home
    returned is the new record's, while the pid checked was the old one's. It also costs a second read on every
    launch, status and log call. Found by two reviewers (one as a cleanup).
  - **Fix.** `found = _agent_record(port)`, then `return _home_in(found[1]) if found else None`.
  - **Resolution: done.**
    - **Test:** `test_the_home_comes_from_the_record_whose_designer_was_checked` (test_lifecycle_env.py) gives two
      reads of the record two different records. It failed with `'/b/home' == '/a/home'`: the home came from the
      second read.
    - **Cause:** `_agent_home` let `_agent_designer` check one read of the record, then read the file again for the
      home.
    - **Fix:** it takes the home from the bytes `_agent_record` checked.
    - **Also covered:** `_agent_record`'s other callers (server_tools/lifecycle.py). `_agent_designer` and the exit
      watch at line 1139 use only the pid. The callers at lines 903 and 1333 (`_quit`) use the bytes they checked.
  - Questioned by SRV-174 (2026-11-17).

- [x] **SRV-173 · JSON read from a file is typed as a TypedDict before it is checked, so a non-object escapes the callers' `except`** · `mcp_server/server_tools/snapshots.py:124-129`, `install.py:160-162`, `uninstall.py:100` · confirmed · found 2026-11-17
  - **Defect.** `note: _Note = json.load(f)` (`_read_note`), `cast(_PluginInfo, json.load(info)).get('name')`
    (`_plugin_name`, whose docstring says "AttributeError when it isn't an object") and `config: _ClaudeConfig =
    json.load(f)` (`find_registrations`) tell mypy the value is a dict. Their callers catch only `(OSError,
    ValueError)`, then call `.get()` on it or index it. AGENTS.md: parsed JSON is `object` until checked, which makes
    the checks explicit; uninstall's `changed_since` shows the checked form.
  - **Scenario.** A snapshot note holding `[]` makes `list_snapshots`, and `diff_graph` against 'latest', fail with
    "'list' object has no attribute 'get'". A `pluginInfo.json` holding a JSON array in the plugin's folder makes
    `install.py` stop with a traceback instead of saying the folder isn't this project's plugin. The behaviour
    predates the branch; the new types hide it from mypy.
  - **Fix.** Read each as `Json`, raise ValueError when it isn't a dict, then return it typed (`_read_note`,
    `_plugin_name`); check the same way in `find_registrations`. Unit tests with a note and a pluginInfo.json holding
    `[]`.
  - **Resolution: done.**
    - **Test:** `test_a_note_holding_no_json_object_reads_as_no_note` (test_snapshots.py),
      `test_a_plugin_info_holding_no_json_object_is_not_this_projects` (test_install.py) and
      `test_a_config_holding_no_json_object_where_one_belongs_finds_no_registration` (test_uninstall.py), with a
      list, a string, and text that isn't JSON. Every case but the last failed with AttributeError ("'list' object has
      no attribute 'get'", and the same for 'str' and `.items`).
    - **Cause:** each reader took the parsed JSON for the dict its type named. A value of another JSON type then
      raised AttributeError, which the callers' `except (OSError, ValueError)` doesn't catch.
    - **Fix:**
      - `_read_note` and `install._plugin_name` read the value as `Json` and raise ValueError when it isn't an object,
        so their callers take it as they take a file that isn't JSON. `_plugin_name` returns a name only when it is a
        string.
      - `find_registrations` checks each level of ~/.claude.json (`_object`): a part that isn't an object counts as
        absent. `_points_here` takes `command` only when it is a string, and `args` only when it is a list. The
        TypedDicts that only described the unchecked shape (`_PluginInfo`, `_ClaudeConfig`, `_Project`,
        `_Registration`) are gone.
    - **Also covered:** every `json.load` and `json.loads` whose result is typed as a TypedDict. Those left read what
      this project's own code wrote, so a value of another type is a bug there and fails loudly: the plugin's signed
      reply (`Reply`), the helpers' printed lines (measure.py's `_NodePixels` and `_SweepTile`), a worker's results
      file, and the self-test's own readers. `read_agent_record` (project_constants.py) is for the tests, and its
      docstring says it checks nothing.
  - Questioned by INS-41, TST-490 (2026-11-17).

- [x] **INS-40 · On Python 3.8, `project_constants.py` fails at import, so `install.py` stops with a traceback** · `project_constants.py:36-42`, `designer_preferences.py:61` · confirmed · found 2026-11-17
  - **Defect.** `Json = Union[..., list['Json'], dict[str, 'Json'], None]`, `JsonSent = Union[...,
    Sequence['JsonSent'], Mapping[str, 'JsonSent'], None]` and `Plist = Union[..., list['Plist'], dict[str,
    'Plist'], None]` are module-level aliases, evaluated even with `from __future__ import annotations`. Subscripting
    `list`, `dict` and the `collections.abc` classes needs Python 3.9 (PEP 585).
  - **Scenario.** `python3.8 install.py` dies with "TypeError: 'type' object is not subscriptable" before its
    "Python 3.10+ is required" message, which main reached; so do `client/sd_run.py` and `scripts/read_crash_dump.py`.
    install.py's and sd_run.py's comments say they "must run, or refuse with a message, on the system Python, which
    can be older than 3.10" (REVIEW.md INS-25), README.md says install.py and uninstall.py start on an older
    `python3`, and `tests/unit/test_old_python.py` lists `python3.8` among its candidates. Low: uninstall.py already
    failed on 3.8 on main (`Callable[[], 'str | None']` from `collections.abc`), and this Mac's `/usr/bin/python3` is
    3.9.6, so the floor was 3.9 in practice, as AGENTS.md's "maybe 3.9" says.
  - **Fix.** State 3.9 as the floor (drop `python3.8` from `CANDIDATES`, say 3.9 in the INS-25 comments and
    README.md), or build the evaluated aliases from `typing.List`, `Dict`, `Sequence` and `Mapping`, with a noqa.
  - **Resolution: done.** The user chose 3.9 as the oldest Python, and DECISIONS.md, Project rules, records it.
    - **Test:** none can fail here: no Python 3.8 is installed, and the decision makes 3.8 unsupported.
      `tests/unit/test_old_python.py` now runs the scripts on a Python 3.9 only. Before, it would take any Python
      older than 3.10.
    - **Fix:** `python3.8` dropped from `CANDIDATES`. install.py's, uninstall.py's, sd_run.py's and scripts/'s
      comments, README.md's requirements and AGENTS.md's typing paragraph say 3.9 or later.
  - Questioned by TST-492 (2026-11-17).

- [x] **TST-480 · Fakes annotated with a type their value doesn't have** · `tests/unit/test_lifecycle_env.py:3880`, `tests/unit/test_view3d_helpers.py:1212`, `:1429`, `tests/unit/test_mac_window.py:96` · confirmed · found 2026-11-17
  - **Defect.**
    - `not_found(opener: 'subprocess.Popen[bytes]', ...)` receives the `_FakeProcess` its test's `_launch_fakes`
      builds; its neighbour `found` types the same parameter `_FakeProcess`, and `marks` `tuple[str, ...]` where
      `not_found` says `Sequence[str]`.
    - Two `taking` fakes return `Callable[[], None]` (`lambda: mouse.sent.append(...)`, `lambda:
      done.append('taken')`) and are passed to `_drag` and `_wheel`, whose `taking` is now `Callable[[],
      Callable[[], bool]]`: the branch's last narrowing of `taking` missed them.
    - `waited: list[tuple[bool, float, list[QtCore.SignalInstance]]]` holds the fake spy's `fired='the Expose
      signal'`, a str. The `until` fakes in test_frames3d.py (:317, :350, :408, :591, :627) and test_mac_window.py
      (:98, :200) type `signals` as `_until`'s real `Sequence['QtCore.SignalInstance']` while receiving such strings,
      and test_frames3d.py:483 types it as what its fake passes.
  - **Scenario.** None at run time: mypy checks none of these calls, made through `patch_server` or the helpers
    module (ROADMAP item 104). The annotations describe values that never arrive, which item 98 set out to remove.
  - **Fix.** `opener: _FakeProcess`, and one `marks` type in both fakes. The `taking` fakes return a function that
    appends, then returns True, typed `Callable[[], bool]`. `waited`'s list of `QtCore.SignalInstance | str`, and one
    convention for the `until` fakes.
  - **Resolution: done.**
    - **Fix:**
      - `not_found` and `found` take `opener: _FakeProcess` and `marks: tuple[str, ...]`, what `_launch_marks` gives.
      - The two `taking` fakes return a `taken()` that records, then returns True, typed `Callable[[], bool]`.
      - The `until` fakes in test_frames3d.py and test_mac_window.py take `signals: Sequence[str]`, the fake spies'
        `fired` (test_frames3d.py:445 keeps its tuples), and `waited` holds `list[str]`.
  - Questioned by TST-489 (2026-11-17).

- [x] **TST-481 · Two records with known keys in test_selftest_pool are typed as wide unions** · `tests/unit/test_selftest_pool.py:339`, `:393` · confirmed · found 2026-11-17
  - **Defect.** `ran: list[tuple[int, bool] | tuple[str, dict[str, str | bool | None]]]` holds `one_run`'s keywords
    (`worker`, `results_file`, `first`), and `seen: dict[str, list[Step] | str | bool | None]` always has the keys
    `steps`, `worker` and `first`. AGENTS.md: a TypedDict for a dict with known keys.
  - **Scenario.** None at run time: a misspelt key, or a value of the wrong member of the union, type-checks.
  - **Fix.** A TypedDict for each (`total=False` for `one_run`'s keywords).
  - **Resolution: done.**
    - **Fix:** `_OneRun` (`total=False`) and `_Run` TypedDicts. The `one_run` fake takes `**kw: Unpack[_OneRun]`.
      `seen` is a list of `_Run`, one per run, so the check also says run was called once.

- [x] **TST-482 · A `cast(str, ...)` hides a None that the next assertion accepts** · `tests/unit/test_snapshots.py:244` · confirmed · found 2026-11-17
  - **Defect.** `fresh = cast(str, root.find('fileUID').get('v'))  # type: ignore[union-attr]`, then `assert fresh
    not in (U, '0') and ...`. `get('v')` is `str | None`, and `None not in (U, '0')` holds. Main had the same check
    without the cast; the cast now tells mypy the None can't happen.
  - **Scenario.** The snapshot's re-stamp writes the package's `<fileUID>` without its `v`: `fresh` is None, the
    first assertion passes, and the test goes on with `PACKAGE_UID=None`.
  - **Fix.** Check instead of cast: `uid = root.find('fileUID')`, `assert uid is not None`, `fresh = uid.get('v')`,
    `assert fresh is not None and fresh not in (U, '0')`.
  - **Resolution: done.**
    - **Fix:** the cast is gone. The test asserts that the package's `<fileUID>` exists and that its `v` is not None,
      before comparing it.

- [x] **TST-483 · A new comment says the elements a Designer script looks for are in every file Designer saves** · `tests/test_all_tools/designer_scripts/shared/graph_parameter_function.py:58` · confirmed · found 2026-11-17
  - **Defect.** "The elements looked for are in every file Designer saves. A missing one raises, which fails the
    script." The node-level `outputsize` `<parameter>` it moves exists only because the script gave the uniform's
    `$outputsize` a function before saving, and a `<parameters>` block holding a `<parameter>` only for a node with a
    parameter set.
  - **Scenario.** A reader reusing `child()` on another .sbs, trusting the comment, meets AttributeError, TypeError
    or StopIteration.
  - **Fix.** "The elements looked for are in the file this script has just saved. A missing one raises, which fails
    the script."
  - **Resolution: done.**
    - **Fix:** "The elements looked for are in the file this script has just saved."

- [x] **TST-484 · New parsing helpers went into editor_panels_and_fit/checks.py instead of a module beside it** · `tests/test_all_tools/editor_panels_and_fit/checks.py:845-893` · confirmed · found 2026-11-17
  - **Defect.** `Printed`, the retyped `_read` and four new TypeGuards (`_events`, `_counts`, `_asks_hidden`,
    `_pairs`) parse what snippets print, in a checks file of over 2,000 lines. AGENTS.md, "Keep each file to its main
    logic": such scaffolding goes in a module of its own beside it, for new code and code a change touches.
  - **Scenario.** A reader of the category's checks meets the parsing before the checks that use it.
  - **Fix.** Move them to a module beside it (`editor_panels_and_fit/printed.py`) and import them. A move changes no
    behaviour, so the existing tests run before and after it.
  - **Resolution: done.**
    - **Fix:** `Printed`, the reader and the four TypeGuards moved to `editor_panels_and_fit/printed.py`, with public
      names: `read_value`, `is_events`, `is_counts`, `is_asks_hidden` and `is_pairs`. checks.py imports them. A move
      changes no behaviour: the self-test's unit tests passed before and after, and so did the category in its scratch
      run.
  - Questioned by TST-491 (2026-11-17).

- [x] **TST-485 · No test holds the tools' pinned JSON schemas** · `mcp_server/server_tools/edits.py:47-51`, `measure.py:222-223`, `scripting.py:30-35`, `ROADMAP.md` item 98 · confirmed · found 2026-11-17
  - **Defect.** The comments and item 98's note say the schemas of `apply_edits`' `ops`, `sweep_param`'s `values`
    and `run_designer_script`'s `args` are pinned to the ones agents saw before. `tests/unit/test_server.py:42`
    records only each tool's property names, and nothing compares the schemas. Their equality was checked by hand on
    this branch: every tool's schema, dumped on main and on the branch, differed only in run_designer_script's
    description.
  - **Scenario.** A pydantic upgrade, or an edit of the aliases, changes what agents are sent, and every test passes.
  - **Fix.** A unit test asserting that those three properties' `input_schema` (from `_list_tools`) equal the schemas
    agents saw. AGENTS.md: a claim without a test is tested or removed.
  - **Resolution: done.**
    - **Test:** `test_the_json_parameters_keep_the_schemas_agents_saw` (test_server.py) compares the three parameters'
      schemas, from a server's `list_tools`, with the ones agents saw on main. It passes. With `JsonObject`'s
      `WithJsonSchema` changed for a run, it failed for `apply_edits.ops` and `run_designer_script.args`.

- [x] **TST-486 · The docs say the plugin keeps its own copies of the bridge's message types; it has only `Reply`** · `AGENTS.md:261-262`, `project_constants.py:44-45` · confirmed · found 2026-11-17
  - **Defect.** AGENTS.md: "Its messages' types (`Request`, `Reply`, `Greeting`) are defined once, in
    `project_constants.py`; the plugin, which can't import it, has its own." project_constants.py: "The plugin keeps
    its own copies". The plugin defines `Reply` (`__init__.py:74`) and reads requests as `_Json`: it has no
    counterpart of `Greeting`, `ScriptRequest` or `ControlRequest`.
  - **Scenario.** Someone changing a request's fields looks for the plugin's own request type, to update it too, and
    finds none.
  - **Fix.** "...; the plugin, which can't import it, has its own `Reply`", in both places.
  - **Resolution: done.**
    - **Fix:** AGENTS.md and project_constants.py say the plugin has its own `Reply` and reads requests as plain JSON.

- [x] **TST-487 · `AgentRecord`'s docstring says the readers check what they read, above a reader that checks nothing** · `project_constants.py:113`, `:120-125` · confirmed · found 2026-11-17
  - **Defect.** `AgentRecord`: "The readers check what they read." `read_agent_record`, right after it: "The tests
    read records with it, and it checks nothing."
  - **Scenario.** A reader takes `read_agent_record` for a checked reader, and uses it outside the tests.
  - **Fix.** Say that the server's reader (`_agent_record`, server_tools/lifecycle.py) checks what it reads, and
    `read_agent_record`, for the tests, doesn't. Or move `read_agent_record` and `ToolArgs`, which only the tests use,
    to `tests/test_all_tools/common.py` (AGENTS.md, "Keep each file to its main logic").
  - **Resolution: done.** The user chose the docstring over moving the reader.
    - **Fix:** `AgentRecord`'s docstring says the server's reader (`_agent_record`) checks what it reads, and
      `read_agent_record`, for the tests, doesn't.

- [x] **TST-488 · ROADMAP item 104 counts 753 `server.X` uses, where 744 are the server module's** · `ROADMAP.md:88` · confirmed · found 2026-11-17
  - **Defect.** The count came from `grep -ohE '\bserver\.[A-Za-z_]+' tests/unit`, which also matches 7
    `mcp.server.…` import paths and the inner `.server.call_tool` of 2 `server.server.call_tool` calls. `git grep
    -ohP "(?<![\w.])server\.\w+" -- 'tests/unit/*.py'` gives 744.
  - **Scenario.** A reader checking the figure gets another number.
  - **Fix.** Say 744, or "about 750".

  - **Resolution: done.**
    - **Fix:** item 104 says 744.

- [x] **PLG-44 · A job's own `@overload` keeps that job's scope alive, as the helpers' did · follows HLP-182, generation 2** · `plugin/sd_claude_bridge_kve/sd_claude_bridge_kve/__init__.py:221`, `:272` · confirmed · found 2026-11-17
  - **Defect.** HLP-182's cause is in the plugin's job model: every job runs as `__main__` (`scope = {'__name__':
    '__main__', ...}`, then `exec(compiled, scope)`), and `typing.overload` keeps each stub it decorates, whose
    globals are that scope. HLP-182's fix removed only the helpers' own overloads.
  - **Scenario.** A script run through `run_designer_script` or `execute_designer_code` uses `@overload`, as a
    mypy-checked script may (run_designer_script's description invites them). Its scope stays alive until a later
    job's stubs take the same keys, or until Designer quits, with whatever sd objects or Qt wrappers it holds. Stubs
    with names or lines of their own pile up. HLP-182's live check measured the mechanism in Designer (`HELD`).
  - **Fix.** The plugin drops what a job left in the registry once it ends (`typing._overload_registry.pop('__main__',
    None)`, or `typing.clear_overloads()`), with a unit test of the plugin and a live check; or a line in GUIDE.md's
    scripting part saying to avoid `@overload` in scripts.
  - **Resolution: done.**
    - **Test:** `test_what_typing_keeps_of_a_job_leaves_its_scope_to_be_freed[overload]` (tests/unit/test_plugin.py)
      runs a job through the plugin's `_run` that decorates its own functions with `@overload`, and checks that an
      object only its scope held is freed. It failed: "the job ended, its scope still held". The live check
      `check_a_jobs_own_overload_leaves_its_scope_to_be_freed` (bridge) does the same across two
      `execute_designer_code` jobs. In its scratch run it failed with `HELD`, then passed with `FREED` once the plugin
      was installed and the agent's Designer restarted.
    - **Cause:** every job runs as `__main__`, and `typing.overload` keeps each stub it decorates under its module's
      name. A stub's globals are its job's scope, so the registry kept that scope alive after the job.
    - **Fix:** once a job ends, the plugin's `_run` drops what `typing._overload_registry` holds under `__main__`, in
      the `finally` that puts the tracer and hooks back. `_send`'s docstring (mac_window.py) now says the plugin drops
      the stubs, and that the helpers keep no `@overload` because a plugin installed before this fix kept the scope.
    - **Also covered:** the plugin's `exec` is its only place that runs code. `run_designer_script`,
      `execute_designer_code`, the helpers and `client/sd_run.py` all reach it. HLP-182's live check still passes.

- [x] **SRV-174 · `_log_for` still reads the agent record twice · follows SRV-172, generation 2** · `mcp_server/server_tools/log.py:56-57` · confirmed · found 2026-11-17
  - **Defect.** `if _agent_designer(port) is not None:` then `home = _agent_home(port)`: each reads the record and
    checks its Designer, with a process listing each. SRV-172's "Also covered" searched only `_agent_record`'s callers
    in lifecycle.py.
  - **Scenario.** Another server's `quit_designer` ends the agent's Designer on the port, and removes its record,
    between the two reads: `_agent_home` gives None, and `read_designer_log` returns the shared log, the user's lines,
    where its docstring promises that Designer's own. Without the race, every log call costs two reads and two
    listings.
  - **Fix.** `found = _agent_record(port)`, then the home from `_home_in(found[1])`. A test whose `_record_bytes` fake
    gives a record, then None.
  - **Resolution: done.**
    - **Test:** `test_the_log_comes_from_the_record_whose_designer_was_checked` (tests/unit/test_lifecycle_env.py):
      `_record_bytes` gives a record, then None, as a quit by another server would. It failed: `_log_for` returned the
      shared log, not the agent's own.
    - **Cause:** `_log_for` checked the Designer with `_agent_designer`, then read the home with `_agent_home`: two
      reads of the record, each with a process listing.
    - **Fix:** `_log_for` reads the record once with `_agent_record` and takes the home from it with `_home_in`.
    - **Also covered:** every caller of `_agent_designer`, `_agent_home` and `_agent_record` in server_tools. None
      other reads the record twice for one decision. `_quit_evidence` reads it once, and `_agent_log` reads no record.

- [x] **HLP-185 · The reworded comments still say more than the code does · follows HLP-183, generation 2** · `mcp_server/designer_helpers/batch.py:48-50`, `mcp_server/designer_helpers/edits.py:65-67`, `mcp_server/designer_helpers/graph_inputs.py:124` · confirmed · found 2026-11-17
  - **Defect.**
    - EditOp's comment says an exposed input's label "is stored as given", but `label or input_id.replace('_',
      ' ').capitalize()` gives an empty, zero or False label the default.
    - "Stored as given: a bool as a bool, a number as a float, anything else as text" says what Designer keeps, which
      no check measures. The code builds those SDValues for `setPropertyAnnotationValueFromId`.
    - `_make_value`'s docstring names `as_bool`'s refusal of a string, but not that it takes any other value by its
      truth: `bool([0])` is True, so a bool parameter takes `[false]` as True, with no refusal.
  - **Scenario.** An agent sends `{"op": "set", "params": {"some_bool": [false]}}` and gets True. A maintainer trusting
    "stored as given" doesn't expect `label: ''` to become the input's id.
  - **Fix.** Narrow both texts to what the code does: an empty label takes the default; the values are built as
    those SDValues; a bool parameter takes a value that isn't a string by its truth.
  - **Resolution: done.**
    - **Test:** none: comments only, no behaviour changed.
    - **Fix:** EditOp's comment says an exposed input's fields are set as SDValues built from them, and that an empty,
      zero, false or null label takes the default made from the input id. `_make_value`'s docstring says a bool
      parameter takes a value that isn't a string by its truth, so `[false]` gives True.
    - **Also covered:** "as given" searched in the helpers, the tools and the docs. The tools' docstring says nothing
      about an exposed input's label.

- [x] **INS-41 · `_plugin_name` reads the JSON as `object`, not `Json` as SRV-173's resolution says, and `find_registrations`' scope is typed `str` · follows SRV-173, generation 2** · `install.py:156`, `uninstall.py:80` · confirmed · found 2026-11-17
  - **Defect.** `parsed: object = json.load(info)`, then `isinstance(parsed, dict)`: mypy narrows it to `dict[Any,
    Any]`, so `name` is `Any | None` and nothing is checked through it (measured with mypy by the reviewer). `Json`,
    which install.py can import from project_constants, narrows to `dict[str, Json]`. `find_registrations` returns
    `list[tuple[str, str | None]]`, its scope only `'user'` or `'local'`.
  - **Scenario.** None at run time: the resolution misdescribes the code, and the types say less than is known.
  - **Fix.** `parsed: Json = json.load(info)`, and `Literal['user', 'local']` for the scope.
  - **Resolution: done.**
    - **Test:** none: types only. mypy strict (tests/unit/test_types.py) passes.
    - **Fix:** `_plugin_name` reads `parsed: Json` (install.py now imports `Json` from project_constants), so `name`
      is `Json`. `find_registrations` and `remove_registration` type the scope `Literal['user', 'local']`.

- [x] **TST-489 · Fakes still annotated with types their values don't have · follows TST-480, generation 2** · `tests/unit/test_mac_window.py:92`, `:94`, `:196`, `tests/unit/test_shot3d.py:221`, `:573`, `tests/unit/test_frames3d.py:304`, `:362`, `:545`, `:641`, `tests/unit/test_shot3d.py:1079` · confirmed · found 2026-11-17
  - **Defect.**
    - test_mac_window.py's `waited: list[tuple[bool, float, list[str]]]`, commented "each wait's signals: the fake
      spies' fired", and its `until(..., signals: Sequence[str])`: the first wait `give_back_activation` makes is given
      the faked app's `applicationStateChanged`, a MagicMock, as the test's own assertion says; only the second gets
      the spy's string. TST-480's fix suggested `QtCore.SignalInstance | str`.
    - test_shot3d.py's `until` fakes keep `Sequence['QtCore.SignalInstance']` while the file's fake spies give
      strings (`fired='its signal'`).
    - The `event_signal` fakes type `watched: 'QtCore.QObject'` and receive the tests' SimpleNamespace stand-ins
      (test_frames3d.py:440 and test_mac_window.py:104 type the same parameter `SimpleNamespace`).
  - **Scenario.** None at run time (mypy checks none of these calls); the annotations describe values that never
    arrive.
  - **Fix.** `QtCore.SignalInstance | str` in test_mac_window.py, with the comment corrected; `Sequence[str]` in
    test_shot3d.py; `SimpleNamespace` for the `event_signal` fakes' `watched`.
  - **Resolution: done.**
    - **Test:** none: annotations only. Measured first by recording what each fake receives in its tests: both of
      test_mac_window.py's `until` fakes get a faked Qt signal and a string; test_shot3d.py's get strings only; the
      five `event_signal` fakes get only SimpleNamespace stand-ins.
    - **Fix:** `Sequence['QtCore.SignalInstance | str']` for test_mac_window.py's `until` fakes and `waited`, with
      its comment saying which signal comes first; `Sequence[str]` for test_shot3d.py's; `SimpleNamespace` for the
      `event_signal` fakes' `watched`, in test_frames3d.py (four) and test_shot3d.py (one).

- [x] **TST-490 · SRV-173's fix is tested only in part: `_points_here`'s checks have no test, and one new assertion passes without the fix · follows SRV-173, generation 2** · `tests/unit/test_uninstall.py:742`, `tests/unit/test_snapshots.py:428` · confirmed · found 2026-11-17
  - **Defect.**
    - None of the eight cases of `test_a_config_holding_no_json_object_where_one_belongs_finds_no_registration`
      reaches `_points_here`. Main's `[entry.get('command') or ''] + [str(a) for a in entry.get('args') or []]` raised
      TypeError for `"command": 5` (`os.path.normcase(5)`) and for `"args": 5`, past `except (OSError, ValueError)`.
      With either check reverted, every test passes.
    - `assert snapshots._changed_since(str(path)) is False  # no size or time noted: can't tell` holds on the old
      code for all three notes: `'size' not in []` and `'size' not in 'text'` are True, and text that isn't JSON is
      caught. The notes that made the old `_changed_since` raise are a number or null (`'size' not in 5`: TypeError),
      and none is tested. With the fix, the comment's reason is also wrong: the note reads as none.
  - **Scenario.** A revert of `_points_here`'s checks, or of `_read_note`'s, passes every test, and uninstall or
    `list_snapshots` stops with a traceback again. Found by two reviewers.
  - **Fix.** Two cases in the config test, `{"mcpServers": {"substance-designer": {"command": 5}}}` and `{..."args":
    5}`, each expecting `([], ['a user-scope "substance-designer" that runs something else'])`; `'5'` and `'null'` in
    the note test's parametrization, and its comment "no note: can't tell".
  - **Resolution: done.**
    - **Test:** `test_a_registration_whose_command_or_args_have_another_type_runs_something_else`
      (tests/unit/test_uninstall.py): a command that is a number, args that are a number, at user scope and in a
      project. The note test takes a number and null too, and its comment says "no note: can't tell". With
      `_points_here`'s checks and `_read_note`'s reverted, all three new cases and four of the note's failed with
      TypeError or AttributeError. With them back, all pass.
    - **Fix:** the tests above. SRV-173's code was already right.

- [x] **TST-491 · A comment names a TypeGuard that was renamed · follows TST-484, generation 2** · `tests/test_all_tools/editor_panels_and_fit/checks.py:895` · confirmed · found 2026-11-17
  - **Defect.** "# _restarted is true only for a list. _counts tells the checker so." `_counts` is now
    `printed.is_counts`.
  - **Scenario.** A reader looks for `_counts` and finds nothing, or `frames._counts`, an unrelated attribute.
  - **Fix.** "`is_counts` tells the checker so."
  - **Resolution: done.**
    - **Fix:** the comment names `is_counts`.

- [x] **TST-492 · test_old_python.py's docstring still says "a Python older than 3.10" · follows INS-40, generation 2** · `tests/unit/test_old_python.py:1-4` · confirmed · found 2026-11-17
  - **Defect.** "The standalone scripts still behave on a Python older than 3.10 ... Skipped when no such interpreter
    is installed." The test now takes only a Python 3.9, and skips with "no Python 3.9 installed".
  - **Scenario.** A reader with only Python 3.8 installed expects the test to run on it, or takes the skip for a fault.
  - **Fix.** "...still behave on Python 3.9, the oldest supported (DECISIONS.md, Project rules) ... Skipped when no
    Python 3.9 is installed."
  - **Resolution: done.**
    - **Fix:** the docstring says Python 3.9, the oldest supported, and that the test is skipped when no Python 3.9 is
      installed.

- [x] **TST-493 · `untraced`'s comment says only `Callable[..., T]` names both functions and classes; a Protocol with `__code__` does** · `tests/unit/aborts.py:38` · measured · found 2026-11-17
  - **Defect.** `untraced: Collection[object] = (),  # functions and classes: only Callable[..., T] names both, an
    explicit Any`. Measured with mypy strict and `--disallow-any-explicit` on a scratch file: a Protocol with a
    `__code__: CodeType` property, unioned with `type`, takes a `def`, a lambda, a class and a SimpleNamespace's
    lambda, refuses an int, and has no explicit Any.
  - **Scenario.** A caller passes something that is neither, such as `tree` instead of `tree.viewport`: it
    type-checks, `_codes` finds no code in it, and the fake it stands for is traced, so aborts land where Designer's
    C++ code would be.
  - **Fix.** `untraced: Collection[_HasCode | type]` with the Protocol in aborts.py, and the comment gone.
  - **Resolution: done.**
    - **Test:** none: types only. mypy strict passes for every caller (test_put_backs.py, test_shot3d.py).
    - **Fix:** `untraced: Collection[_HasCode | type]`, with `_HasCode` a Protocol in aborts.py whose `__code__` is a
      `CodeType`. The comment is gone.

- [x] **TST-494 · The new DECISIONS.md entry cites a review finding, which the file's header rules out** · `DECISIONS.md:56` · confirmed · found 2026-11-17
  - **Defect.** "...and `uninstall.py` already needed 3.9 (REVIEW.md INS-40)." The header: "Entries don't cite review
    findings." INS-40 leaves REVIEW.md at its next cleanup.
  - **Scenario.** A reader of DECISIONS.md follows an ID that a cleanup removed (the lookup still finds it).
  - **Fix.** Drop "(REVIEW.md INS-40)": a name or reference, not what was decided.
  - **Resolution: done.**
    - **Fix:** the entry no longer cites INS-40. What was decided is unchanged.

- [x] **TST-495 · ROADMAP item 105's plan misses the venv an older Python made, and three "3.10+" places** · `ROADMAP.md:89` · confirmed · found 2026-11-17
  - **Defect.** The plan has `install.py` refuse a Python below 3.12, but `install.py:277` keeps any venv that still
    runs (`if not venv_runs(py):`): a user who installed with 3.10 keeps a 3.10 venv after re-running install.py with
    3.12, and the server then starts on 3.10 with code written for 3.12. The plan also leaves out README.md:33 ("a
    separate Python 3.10+ process"), README.md:121 ("a Python 3.10+ python.exe") and install.py's docstring ("Run it
    with a Python 3.10+ interpreter").
  - **Scenario.** Item 105 done as planned: an existing install keeps running the server on 3.10, and breaks on the
    first 3.11 or 3.12 feature the code uses.
  - **Fix.** Add to the plan: a venv made by a Python older than 3.12 is made again, with its test; and the three
    places.
  - **Resolution: done.**
    - **Fix:** item 105's plan says `install.py` makes the venv again when an older Python made it, with a unit test.
      It also lists README.md's two "3.10+" places, `install.py`'s docstring and its comment on the system Python.

- [x] **PLG-45 · typing's subscription caches keep a job's scope alive, as its overload registry did · found while addressing PLG-44** · `plugin/sd_claude_bridge_kve/sd_claude_bridge_kve/__init__.py:286` · measured · found 2026-11-17
  - **Defect.** typing caches every subscription it builds (`_tp_cache`, an LRU cache of 128 entries per function).
    A job that subscripts with its own class, as in `Optional[Kept]`, `List[Kept]` or a subscripted `Generic`
    subclass, leaves the class in the cache. The class's methods have the job's scope as their globals, so the scope
    stays alive after the job. Found by the /simplify pass's altitude reviewer.
  - **Scenario.** A mypy-checked script run through `run_designer_script` annotates with `Optional[...]` of its own
    class. Its scope stays alive, with the sd objects and Qt wrappers it holds, until the cache drops the entry. Each
    job makes new classes, so new entries pile up, up to 128 per cached function. Measured on the venv's Python 3.12:
    an object only the job's scope held stayed alive for each of the three forms; `Kept | None` was freed. The helpers
    use none of these forms.
  - **Fix.** The plugin clears typing's caches once a job ends, with the overload registry.
  - **Resolution: done.**
    - **Test:** `test_what_typing_keeps_of_a_job_leaves_its_scope_to_be_freed` (tests/unit/test_plugin.py), its
      `Optional`, `List` and `Generic` cases. All three failed: "the job ended, its scope still held". The live check
      `check_a_jobs_typing_subscripts_leave_its_scope_to_be_freed` (bridge) runs the three forms in one job. In its
      scratch run it failed with `HELD` on Designer's Python 3.13, then passed with `FREED` once the plugin was
      installed and the agent's Designer restarted.
    - **Cause:** typing's subscription caches keep the classes a job subscripts with. Their methods' globals are the
      job's scope.
    - **Fix:** the plugin's `_run` calls each function in `typing._cleanups` (each cache's `cache_clear`) once a job
      ends, beside the overload registry's clean-up. Typing then rebuilds a subscription on its next use.
    - **Also covered:** a scope cleared once its job ends would free it whatever holds it, but `_after_reply`
      callbacks and a script's own Qt slots run after the job and read its globals. The three scope checks now share
      one helper, in bridge/scope_jobs.py.
