---
name: babysit-pr
description: Use when asked to babysit a GitHub PR.
---

# Babysit PR

Fix review feedback and CI failures in rounds until each PR reaches an end
state. This skill runs unattended. A stack runs as one loop, bottom up.

1. Run the first round right away, without waiting for running checks. After
   each round, start a background `gh pr checks <pr> --watch` for each PR, or
   schedule a wakeup when checks can outlast a command's time limit, and end
   your turn; the next wake starts the next round. A gated check belongs to a
   workflow run that waits on maintainer approval, which
   `gh run list --commit <head-sha> --status action_required` or
   `--status waiting` lists. Leave gated checks to the user; they are neither
   pending nor failed.
2. At the start of each round, read `isInMergeQueue` and `autoMergeRequest`
   with `gh api graphql`. If either is set and the user hasn't answered for
   this PR yet, raise it and hold the round until they do.
3. Give each round a fresh subagent that runs steps 4 to 7 and returns the head
   and base SHAs it ended on, each fix it attempted, with the thread or failing
   check and the request or error it addressed, and raised items as
   `gh-review-comments`' Raise section describes them, instead of asking. To
   ask the user, stop the watchers, start them again once they answer, and
   pass the answers to that PR's next round.
4. Handle the feedback with `gh-review-comments`, and leave its push to
   step 7.
5. Fix every failed check on the PR's head, including one that also fails on
   the base head. A CI repair counts as part of the PR's purpose. Rerun a
   transient failure once, and raise it if it repeats. Raise a fix that
   changes product behavior beyond the PR's purpose or rests on an
   assumption.
6. Rebase onto the base when the PR conflicts with it or `mergeStateStatus` is
   `BEHIND`. When nothing else is left, also rebase if base commits since the
   last round's base SHA touch files the PR changes. Raise a conflict whose
   resolution needs judgment.
7. Push once, with the CI and feedback fixes together, then finish
   `gh-review-comments` from its Reply section.

When `gh` reports the GraphQL rate limit is used up, wait in the background
until the time `gh api rate_limit --jq .resources.graphql.reset` gives, then
continue the round.

Stop when each PR reaches one of these states on its current head. List
unresolved threads with the `gh-review-comments` fetch script and
`--threads-only`.

- **Merge-ready:** `mergeStateStatus` is `CLEAN` and no unresolved thread is
  left except ones the user kept open.
- **Waiting on people:** every check that isn't gated has finished without a
  failure, and only approvals, gated runs, requested reviewers, or draft
  state remain.
- **Blocked:** a failed check needs the user, a round repeats a fix an
  earlier round tried for the same request or error, or something else
  remains that this loop can't fix. Reruns of transient failures follow
  step 5.

Stop every watcher and cancel any scheduled wakeup before you hand a PR over
or stop. Hand each PR over with its
state, link, head and base SHAs, what changed across rounds, the follow-ups,
and what's left for the user, merging included. For a blocked PR, add what
blocks it and what each round tried.
