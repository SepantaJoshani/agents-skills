#!/usr/bin/env python3

"""Resolve a Git-registered worktree and open it in the macOS Codex app."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Worktree:
    path: Path
    branch: str
    locked: bool


APP_BUNDLE_ID = "com.openai.codex"


def run_git(repo: str, *args: str) -> str:
    repo_path = os.path.expanduser(repo)
    result = subprocess.run(
        ["git", "-C", repo_path, *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Git command failed"
        raise RuntimeError(message)
    return result.stdout


def repository_root(repo: str) -> Path:
    root = run_git(repo, "rev-parse", "--show-toplevel").strip()
    return Path(root).expanduser().resolve()


def parse_worktrees(repo: str) -> list[Worktree]:
    output = run_git(repo, "worktree", "list", "--porcelain")
    records: list[Worktree] = []
    current: dict[str, object] = {}

    def append_current() -> None:
        if "path" not in current:
            return
        records.append(
            Worktree(
                path=Path(str(current["path"])).expanduser().resolve(),
                branch=str(current.get("branch", "(detached)")),
                locked=bool(current.get("locked", False)),
            )
        )

    for line in [*output.splitlines(), ""]:
        if not line:
            append_current()
            current = {}
        elif line.startswith("worktree "):
            current["path"] = line.removeprefix("worktree ")
        elif line.startswith("branch "):
            current["branch"] = line.removeprefix("branch refs/heads/")
        elif line == "detached":
            current["branch"] = "(detached)"
        elif line.startswith("locked"):
            current["locked"] = True

    return records


def candidate_keys(worktree: Worktree) -> set[str]:
    return {
        str(worktree.path),
        worktree.path.name,
        worktree.branch,
        worktree.branch.replace("/", "-"),
    }


def selector_keys(selector: str, repo_root: Path) -> set[str]:
    supplied = Path(os.path.expanduser(selector))
    keys = {selector}
    if supplied.is_absolute():
        keys.add(str(supplied.resolve()))
    else:
        keys.add(str(supplied.resolve()))
        keys.add(str((repo_root / supplied).resolve()))
    return keys


def resolve_selector(
    worktrees: list[Worktree], selector: str, repo_root: Path
) -> list[Worktree]:
    supplied_keys = selector_keys(selector, repo_root)
    exact = [item for item in worktrees if supplied_keys & candidate_keys(item)]
    if exact:
        return exact

    needle = selector.casefold()
    return [
        item
        for item in worktrees
        if any(needle in key.casefold() for key in candidate_keys(item))
    ]


def format_worktrees(
    worktrees: list[Worktree], selected_checkout: Path | None = None
) -> str:
    if not worktrees:
        return "No registered worktrees found."
    width = max(len(item.branch) for item in worktrees)
    lines = []
    for item in worktrees:
        flags = []
        if selected_checkout == item.path:
            flags.append("selected checkout")
        if item.locked:
            flags.append("locked")
        suffix = f" [{', '.join(flags)}]" if flags else ""
        lines.append(f"{item.branch:<{width}}  {item.path}{suffix}")
    return "\n".join(lines)


def open_in_codex(path: Path) -> None:
    if sys.platform != "darwin":
        raise RuntimeError("This skill currently supports the macOS Codex/ChatGPT app only.")

    result = subprocess.run(
        ["open", "-b", APP_BUNDLE_ID, str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "macOS open failed"
        raise RuntimeError(
            f"Could not open the installed Codex app ({APP_BUNDLE_ID}): {detail}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Open an existing Git-registered worktree in the macOS Codex app."
    )
    parser.add_argument("selector", nargs="?", help="Branch, path, directory, or substring")
    parser.add_argument("--repo", default=".", help="Any path inside the repository")
    parser.add_argument("--list", action="store_true", help="List registered worktrees")
    parser.add_argument("--dry-run", action="store_true", help="Resolve without opening the app")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        root = repository_root(args.repo)
        worktrees = parse_worktrees(args.repo)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if args.list:
        print(format_worktrees(worktrees, root))
        return 0

    if not args.selector:
        print("Select a registered worktree:", file=sys.stderr)
        print(format_worktrees(worktrees, root), file=sys.stderr)
        return 2

    matches = resolve_selector(worktrees, args.selector, root)
    if len(matches) != 1:
        heading = "No worktree matched" if not matches else "Selector is ambiguous"
        candidates = worktrees if not matches else matches
        print(f"{heading}: {args.selector}", file=sys.stderr)
        print(format_worktrees(candidates, root), file=sys.stderr)
        return 2

    selected = matches[0]
    if not selected.path.is_dir():
        print(f"error: worktree path does not exist: {selected.path}", file=sys.stderr)
        return 1

    if not args.dry_run:
        try:
            open_in_codex(selected.path)
        except RuntimeError as error:
            print(f"error: {error}", file=sys.stderr)
            return 1

    action = "resolved" if args.dry_run else "opened"
    print(action)
    print(f"branch: {selected.branch}")
    print(f"worktree: {selected.path}")
    if not args.dry_run:
        print("current task: unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
