---
paths:
  - "**/*.md"
  - "**/*.py"
  - "**/*.ini"
  - "**/*.toml"
---

# The docs: where each fact goes, and how to write it

The rules for every doc, docstring and comment (AGENTS.md, Working on this project, points here).

## Keeping the docs current

README.md is for people, AGENTS.md for agents changing this project, `mcp_server/GUIDE.md` for agents driving Designer.
With every change (a tool, a fix, a workaround, a fact learned about
Designer), add a short note where it belongs, in the same change. Keep each fact in **one** place and link to it
instead of copying it; fix or delete notes that turn out wrong rather than adding a contradicting one. One repeat is
deliberate: the sentence saying what REVIEW.md and DECISIONS.md each remember. `docs/agent-workflow.md` retells the
setup for other repositories, by design. It defers to each rule's home, and prefers a pointer there to a copy of
the rule's wording or figures.

| Kind of knowledge | Where it goes |
|---|---|
| How to use the tools well, workflow, sd API / Designer pitfalls, verified facts | **`mcp_server/GUIDE.md`**, in the matching section: the core if an agent using only the tools needs it or every script hits it on the first try, otherwise under `# Scripting` |
| How a tool works around Designer: what only whoever maintains it needs (would an agent using the tools act differently without it?) | The **docstring or comments of its module**, not the tool's docstring, which agents pay for; the guide keeps at most a line and the path |
| A tool's parameters and behaviour | The tool's **docstring in its module of `mcp_server/server_tools/`**, the single source; don't repeat parameters in the guide |
| Install, configuration, security, troubleshooting, anything a **person** needs | **README.md** |
| Architecture: what the plugin, server, helpers and CLI tools each do | **README.md**, "How it works" |
| How to deploy changes, diagnostics an **agent** needs | **AGENTS.md**, Deploying and diagnosing, or the rule or skill it points to for that work |
| New or changed tool | Its entry and the tool count in README.md's Tools table, and checks in `tests/test_all_tools/` |
| What is settled for the whole project that a reviewer could plausibly raise again: the user's won't fix, rule or choice. A false finding (not a bug, not reproducible) stays in REVIEW.md | **DECISIONS.md** (read by the review skills; agents may update its names and paths, anything else takes the user) |
| Work still to do, ideas, follow-ups | **ROADMAP.md** (check an item when done; checked items can be deleted later, git keeps the record) |
| The plan of the branch in progress: what is done, what is left, the decisions waiting | **PLAN.md**, the lead's (AGENTS.md, Working on this project) |
| A rule only some files need | A path-scoped rule in **`.claude/rules/`**, listed in AGENTS.md (Working on this project) |
| A procedure only some work needs | A **skill** in `.claude/skills/`, named in AGENTS.md where the work comes up |
| How the lead and its subagents work, told for other repositories | **`docs/agent-workflow.md`**, updated in the change that alters the setup it tells |

AGENTS.md has a byte budget (`AGENTS_MD_BUDGET` in `tests/unit/test_guide.py`), so what only some work needs goes in a
rule or a skill.

Open work lives in [ROADMAP.md](../../ROADMAP.md): check it before proposing improvements. Propose new ideas to the
user, who decides each one. An idea goes in ROADMAP.md only once they approve it, as the `address-review` skill's
After a group says (`.claude/skills/address-review/SKILL.md`).

## Writing docs and comments

Docs, docstrings, comments and the lines the tools return are read by people and agents who didn't write the code,
often in a hurry. Write them so that one reading, top to bottom, is enough:

- **Subject and verb first.** Say who or what does what: "The first launch saves a copy of the file, unless one is
  there already", not "Saved as the first Designer starts, unless one is there already: a copy of the file".
- **One idea per sentence.** Split a sentence that chains clauses with colons or semicolons into several sentences, or
  into a list.
- **At most one parenthetical per sentence.** Give the others a sentence of their own, or drop them.
- **Name what you mean.** Write "the copy" or "the user's Designer" instead of "it", "one" or "theirs" when the reader
  would have to look back to know which.
- **Plain words.** "If the start fails, a copy made for it is removed. A copy made again is kept", not "A copy made
  here, not again, is removed when the start raises".
- **The main point first.** A docstring opens with what the function does, returns and raises. Reasons, history and
  REVIEW.md IDs come after that, or in a comment beside the line they explain.
- **Lists for parallel cases.** Put three or more cases, steps or exceptions in a list, not in one long sentence.
- **No filler.** Leave out "note that", "it's worth noting", "simply", and words that only add emphasis.

Rewriting for style never changes what a sentence claims. Reviews check each claim against its test, so the new
wording must say exactly what the old one did. This applies to the text you write or change. Don't rewrite untouched
text only for its style: a rewrite can change a claim, and it adds noise to the diff. Reviews report a sentence only
when it misleads, never for its style alone.
