# Matias's agent skills

Matias's reusable agent skills for Claude Code and other coding agents, built
around a GitHub-only workflow.

Third-party skills, such as
[mattpocock/skills](https://github.com/mattpocock/skills), stay installed from
their upstream repositories and aren't copied here.

## Install

List the available skills:

```bash
npx skills add mmenafra/skills --list
```

Install them globally:

```bash
npx skills add mmenafra/skills -g
```

The `skills` CLI owns installation, updates, and lock tracking.

## Skills

The GitHub skills need only the `gh` CLI, authenticated against GitHub.

- [`gh-review-comments`](skills/gh-review-comments/SKILL.md) fetches unresolved
  GitHub review threads, top-level comments, and review bodies, handles routine
  fixes, replies, and resolutions on its own, and raises only the decisions
  that need the user's judgment.
- [`babysit-pr`](skills/babysit-pr/SKILL.md) fixes review feedback and every
  failed check on a PR in rounds through `gh-review-comments`, pushes once per
  round, and hands the PR back as merge-ready, waiting on people, or blocked.
- [`test-plan`](skills/test-plan/SKILL.md) lists the ways a feature could fail
  in prod, plans an end-to-end check for each, probes which checks the agent's
  current access can run, and asks for the access the rest need.
- [`review-revise`](skills/review-revise/SKILL.md) runs adversarial
  review-revise loops with independent subagent reviewers until findings are
  resolved or the loop stalls, 3 rounds by default.
- [`developer-documentation-style`](skills/developer-documentation-style/SKILL.md)
  reads the live Google guide before writing, editing, or reviewing developer
  documentation.
- [`rewrite-it`](skills/rewrite-it/SKILL.md) rewrites text the user points at,
  or the last reply, to be shorter, plainer, and lead with the point.
- [`linkedin-content`](skills/linkedin-content/SKILL.md) drafts LinkedIn
  posts and articles in Matias's voice and formatting rules.
- [`contratos-calle-latina`](skills/contratos-calle-latina/SKILL.md) generates
  Calle Latina Records author/composer contracts as PDFs, one or in bulk. It
  needs Python 3 with `reportlab` and `pypdf`.

Sources that shaped these skills are listed in [REFERENCES.md](REFERENCES.md).

## Repository layout

```text
skills/              Personal skills, one directory each
scripts/             Repository validation
```

## Development

Validation requires Python 3.10+, Git, and Bash, with no Python packages. After
changing a skill or script, stage the changes and run:

```bash
scripts/validate-skills.sh
```

The validator requires a staged snapshot with no unstaged changes or untracked
validation inputs. It checks skill names, description shape, README links,
script executability and syntax, and whitespace errors.

Run the Python tests with pytest, for example through uv:

```bash
uv run --no-project --with pytest pytest scripts/tests skills
```

## License

[MIT](LICENSE)
