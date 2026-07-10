# Validation Checklist

Use this checklist before applying any PR comment.

## Checkout Preconditions

- Confirm the current worktree branch exactly matches the PR head branch.
- Confirm the PR head repository for cross-repository PRs.
- Confirm the target worktree has no pre-existing changes.
- Fetch and compare the PR head without rebasing or merging divergent history.
- Recheck synchronization before every separate review-fix commit.

## Decide Validity

Mark each comment as one of:

- `valid`: technically correct, in scope, and still applies to current HEAD.
- `invalid`: incorrect, unsafe, or contrary to repository conventions.
- `already_fixed`: the issue is absent from current HEAD.
- `out_of_scope`: unrelated to the PR's intended change.
- `needs_clarification`: ambiguous or missing acceptance criteria.

## Validate Automated Feedback

1. Read the complete body and any extracted agent prompt.
2. Verify every referenced file and line against current HEAD.
3. Reproduce the issue or trace the affected code path.
4. Check the recommendation against local instructions and existing utilities.
5. Apply only changes that improve correctness, safety, or maintainability.
6. Ignore deploy/status automation and mechanical suggestions that add no value.

## Validate Human Feedback

1. Identify the reviewer's intent: correctness, scope, product behavior, or style.
2. Confirm the current behavior and affected path.
3. Check side effects, compatibility, and regression risk.
4. Prefer the reviewer's intent over literal wording when they differ.
5. Ask a precise question instead of inventing an external contract.

## Evidence Requirements

Before marking an item `valid`, collect at least one:

- current file-and-line evidence;
- a failing test, check, warning, or linter result;
- a reproducible behavior or traced execution path.

## Implementation Rules

- Handle one comment at a time and keep all of its necessary changes together.
- Never batch distinct comments merely because they touch the same file.
- Keep unrelated cleanup out of the patch.
- Run targeted checks before committing.
- Stage only the files for the current comment.
- Create one local commit per resolved `valid` comment.
- Do not commit rejected, already-fixed, out-of-scope, or unclear items.
- Do not push, post GitHub replies, or resolve threads unless explicitly requested.

## Suggested Status Summary

```text
Addressed:
- <comment URL>: <change> (<file>) | commit <sha>

Not Addressed:
- <comment URL>: <invalid/already_fixed/out_of_scope reason>

Needs Clarification:
- <comment URL>: <specific question>
```
