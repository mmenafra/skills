# Repository guidance

## Scope

- This repository owns Matias's portable personal agent skills.
- Maintain this repository in its existing `main` checkout. Create a branch or
  worktree only when the user asks for one.
- Install third-party skills from their upstream repositories. Keep their source
  out of this repository.
- Keep project-specific skills in the project that owns their assumptions and
  tooling.
- Keep every skill self-contained: it can rely on `gh` and on other skills in
  this repository, but not on user-level instruction files, Linear, Slack, or
  Codex.

## Where each rule goes

A rule reaches a session only through a file that session loads:

| Rule | File | Loaded |
|---|---|---|
| A workflow, its gates, and what it expects from the skills it calls | the skill's `SKILL.md` or `references/` | each session that loads the skill |
| How to write and validate skills | this file | only while editing this repository |

Put no rule an agent needs while running a skill in this file; those sessions
never read it.

## Skill structure

- Put each installable skill under `skills/<name>/`.
- Give every skill a `SKILL.md` whose frontmatter name matches its directory.
- Write each description as one compact, unquoted `Use when <trigger>.`
  sentence of 25 to 64 characters. Name the domain in the trigger, such as "a
  GitHub PR", since no summary of what the skill does precedes it.
- Keep ordered agent steps in `SKILL.md`. Move branch-specific reference
  material behind a direct pointer under `references/`.
- Put repeatable mechanics in `scripts/`. Copy a script into each skill that
  uses it, so every skill installs on its own, and keep same-named copies
  identical.
- Leave every skill model-invokable, so one request can chain several skills
  by their triggers. When a related task shouldn't start the skill, as with one
  that pushes or runs unattended, key the trigger to an explicit request: "Use
  when asked to babysit a GitHub PR."
- A skill that another skill runs leaves the push and the questions to the
  user to its caller when the caller asks.
- Refer to another skill's steps by section heading or by what they do, not
  by step number.
- Add a subagent step only for parallel work, independent review, or a sweep
  whose output only matters as a conclusion. Background:
  [When to fold subagents into your main agent loop](https://claude.com/resources/articles/building-agents-when-to-fold-subagents-into-your-main-agent-loop).
- Key every trigger and stop condition to something the agent can observe when
  it decides: the kind of task, a tool, or a fact in its record.

## Change rules

- Wrap Markdown prose at 80 columns. Leave headings, tables, code blocks, and
  links that can't break as they are.
- Match the concision of the surrounding skill text. Write only what changes
  agent behavior.
- Keep `README.md` and the skill inventory in sync.
- When an article, video, or repository shapes a skill, add it to
  `REFERENCES.md` with what it contributed and the skills it touched.
- Run `scripts/validate-skills.sh` after changing skills or scripts.
- Preserve approval gates for external writes.
- Do not change global installations, global agent guidance, or external
  services as part of a repository edit without explicit approval.
