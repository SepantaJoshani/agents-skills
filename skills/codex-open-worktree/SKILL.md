---
name: codex-open-worktree
description: Open any existing Git-registered worktree as a workspace in the macOS Codex desktop app, including installations branded as ChatGPT. Use when the user asks to open, switch to, move to, or continue in an existing worktree from Codex; invokes `$codex-open-worktree`; supplies a branch name, worktree directory, or worktree path; or wants Codex to discover a repository's worktrees and ask which one to open. Works with worktrees created by Git, Claude, Codex, Supacode, or other tools at any path. Opens a workspace without creating, removing, checking out, or modifying a worktree or branch.
---

# Codex Open Worktree

Open a registered Git worktree in the macOS desktop app without changing Git state. Treat "switch" as "open the selected worktree in another Codex workspace" because the current task cannot be rebound to a different workspace.

## Workflow

1. Resolve the repository from the current directory unless the user supplied a repository or worktree path. If neither path is inside a Git repository, ask for one; do not search the filesystem broadly.
2. If the user supplied a branch, worktree name, or path, run:

   ```bash
   python3 ./scripts/open_worktree.py --repo <repo> <selector>
   ```

   Resolve `./scripts/open_worktree.py` relative to this `SKILL.md`.

   Open immediately when the selector has one exact or unique match. An explicit invocation with a unique selector authorizes this external app action; do not ask for redundant confirmation.

3. If the user supplied no selector, run:

   ```bash
   python3 ./scripts/open_worktree.py --repo <repo> --list
   ```

   Present the registered worktrees and ask which one to open. Put a clearly implied candidate first and label it `(Recommended)`; if intent does not distinguish a candidate, ask neutrally instead of inventing a preference. Never choose silently, even when only one alternative exists.

4. If selection is ambiguous or missing, show the script's candidates and ask the user for one branch or path. Rerun with the exact selection after they answer.
5. After a successful script result, report the opened branch and absolute worktree path. State that the app was asked to open that workspace and the current task remains attached to its original workspace. Stop; do not begin work in either workspace.

## Safety Boundaries

- Open only an existing directory returned by `git worktree list --porcelain` for the selected repository.
- Never run Git commands that mutate worktrees, branches, the index, or files. In particular, never run `git switch`, `git checkout`, `git worktree add`, `git worktree remove`, or `git worktree prune`.
- Never invoke `codex app`, an installer, a package manager, or a download. Use the bundled script, which calls macOS `open` with the installed app's stable bundle identifier only.
- Do not claim the current conversation switched. The app opens or focuses a workspace for the selected folder; this task's workspace and branch indicator do not change.
- Treat an explicit skill invocation with a unique selector as authorization to open that workspace. With no selector, list and ask before opening anything.
- Treat locked worktrees like any other registered worktree. A Git worktree lock affects pruning, not whether its directory can be opened.

## Script Interface

Use `--dry-run` to verify resolution without opening the app:

```bash
python3 ./scripts/open_worktree.py --repo <repo> --dry-run <selector>
```

The selector accepts an exact branch name, absolute or repository-relative path, directory name, flattened branch name such as `feat-example`, or a unique case-insensitive substring. The script exits without opening anything when the selector is absent, ambiguous, unmatched, or resolves to a missing directory.
