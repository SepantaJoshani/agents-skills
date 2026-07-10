#!/usr/bin/env python3
"""Collect and normalize complete GitHub pull-request feedback via gh."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from typing import Any


AI_REVIEWER_LOGINS = frozenset(
    {
        "coderabbitai",
        "copilot-pull-request-reviewer",
        "devin-ai-integration",
        "ellipsis-dev",
        "github-copilot",
        "qodo-merge-pro",
        "sourcery-ai",
    }
)

SOURCE_LABELS = {
    "human": "Human",
    "ai_reviewer": "AI Reviewer",
    "automation": "Automation",
    "unknown": "Unknown",
}

REVIEW_THREADS_QUERY = """
query($owner:String!, $repo:String!, $number:Int!, $cursor:String) {
  repository(owner:$owner, name:$repo) {
    pullRequest(number:$number) {
      reviewThreads(first:100, after:$cursor) {
        nodes {
          id
          isResolved
          isOutdated
          comments(first:1) {
            nodes {
              databaseId
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
  }
}
"""


def run_gh(args: list[str]) -> str:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"gh {' '.join(args)} failed")
    return proc.stdout


def ensure_gh() -> None:
    if shutil.which("gh") is None:
        raise RuntimeError("gh CLI is not installed or not in PATH")
    run_gh(["--version"])
    run_gh(["auth", "status"])


def repo_args(repo: str | None) -> list[str]:
    return ["--repo", repo] if repo else []


def resolve_pr_number(pr: int | None, repo: str | None = None) -> int:
    if pr is not None:
        return pr
    data = json.loads(
        run_gh(["pr", "view", *repo_args(repo), "--json", "number"])
    )
    return int(data["number"])


def parse_repo_from_pr_url(url: str) -> tuple[str, str]:
    match = re.search(r"github\.com/([^/]+)/([^/]+)/pull/\d+", url)
    if not match:
        raise RuntimeError(f"Could not parse owner/repo from PR URL: {url}")
    return match.group(1), match.group(2)


def normalize_login(login: str) -> str:
    normalized = (login or "").strip().casefold()
    if normalized.endswith("[bot]"):
        return normalized[:-5]
    return normalized


def classify_source(login: str, account_type: str | None) -> str:
    normalized = normalize_login(login)
    if normalized in AI_REVIEWER_LOGINS:
        return "ai_reviewer"
    if (account_type or "").casefold() == "bot" or (login or "").casefold().endswith(
        "[bot]"
    ):
        return "automation"
    if not normalized:
        return "unknown"
    return "human"


def body_excerpt(body: str, limit: int = 220) -> str:
    text = " ".join((body or "").split())
    return text[:limit]


def extract_ai_prompts(body: str) -> list[str]:
    if not body:
        return []

    prompts: list[str] = []
    heading_re = re.compile(r"(?is)prompt for ai agents.*?```+[^\n]*\n(.*?)```+")
    prompts.extend(match.group(1).strip() for match in heading_re.finditer(body))

    instruction_re = re.compile(r"(?m)^>?\s*In @.+$")
    prompts.extend(match.group(0).strip() for match in instruction_re.finditer(body))

    seen: set[str] = set()
    unique: list[str] = []
    for prompt in prompts:
        if prompt and prompt not in seen:
            seen.add(prompt)
            unique.append(prompt)
    return unique


def source_fields(login: str, account_type: str | None) -> dict[str, Any]:
    source = classify_source(login, account_type)
    return {
        "source": source,
        "is_ai": source == "ai_reviewer",
        "is_bot": source in {"ai_reviewer", "automation"},
    }


def normalize_top_level(comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for comment in comments:
        author = comment.get("user") or {}
        login = author.get("login", "")
        body = comment.get("body") or ""
        normalized.append(
            {
                "kind": "top_level",
                "id": comment.get("id"),
                "author": login,
                **source_fields(login, author.get("type")),
                "created_at": comment.get("created_at"),
                "url": comment.get("html_url"),
                "body": body,
                "excerpt": body_excerpt(body),
                "ai_prompts": extract_ai_prompts(body),
            }
        )
    return normalized


def normalize_reviews(reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for review in reviews:
        body = review.get("body") or ""
        state = (review.get("state") or "").upper()
        if not body.strip() and state == "COMMENTED":
            continue

        author = review.get("user") or {}
        login = author.get("login", "")
        normalized.append(
            {
                "kind": "review",
                "id": review.get("id"),
                "author": login,
                **source_fields(login, author.get("type")),
                "state": state,
                "submitted_at": review.get("submitted_at"),
                "url": review.get("html_url"),
                "body": body,
                "excerpt": body_excerpt(body),
                "ai_prompts": extract_ai_prompts(body),
            }
        )
    return normalized


def collect_review_thread_status(
    owner: str, repo: str, pr: int
) -> dict[int, dict[str, Any]]:
    by_root_comment_id: dict[int, dict[str, Any]] = {}
    cursor: str | None = None

    while True:
        args = [
            "api",
            "graphql",
            "-f",
            f"owner={owner}",
            "-f",
            f"repo={repo}",
            "-F",
            f"number={pr}",
            "-f",
            f"query={REVIEW_THREADS_QUERY}",
        ]
        if cursor:
            args.extend(["-f", f"cursor={cursor}"])

        response = json.loads(run_gh(args))
        pull_request = (
            response.get("data", {}).get("repository", {}).get("pullRequest")
        )
        if pull_request is None:
            raise RuntimeError(f"PR #{pr} was not found in {owner}/{repo}")
        review_threads = pull_request.get("reviewThreads") or {}

        for thread in review_threads.get("nodes") or []:
            root_comments = (thread.get("comments") or {}).get("nodes") or []
            if not root_comments:
                continue
            root_comment_id = root_comments[0].get("databaseId")
            if root_comment_id is None:
                continue
            by_root_comment_id[int(root_comment_id)] = {
                "thread_id": thread.get("id"),
                "thread_resolved": bool(thread.get("isResolved")),
                "thread_outdated": bool(thread.get("isOutdated")),
            }

        page_info = review_threads.get("pageInfo") or {}
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")
        if not cursor:
            raise RuntimeError("GitHub returned a review-thread page without a cursor")

    return by_root_comment_id


def inline_root_comment_id(comment: dict[str, Any]) -> int | None:
    value = comment.get("in_reply_to_id") or comment.get("id")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_inline(
    comments: list[dict[str, Any]],
    review_thread_status: dict[int, dict[str, Any]],
    include_resolved: bool,
) -> list[dict[str, Any]]:
    normalized = []
    for comment in comments:
        thread_status = review_thread_status.get(inline_root_comment_id(comment))
        if (
            not include_resolved
            and thread_status is not None
            and thread_status.get("thread_resolved")
        ):
            continue

        author = comment.get("user") or {}
        login = author.get("login", "")
        body = comment.get("body") or ""
        normalized.append(
            {
                "kind": "inline",
                "id": comment.get("id"),
                "author": login,
                **source_fields(login, author.get("type")),
                "created_at": comment.get("created_at"),
                "url": comment.get("html_url"),
                "path": comment.get("path"),
                "line": comment.get("line") or comment.get("original_line"),
                "thread_id": thread_status.get("thread_id") if thread_status else None,
                "thread_resolved": (
                    thread_status.get("thread_resolved")
                    if thread_status is not None
                    else None
                ),
                "thread_outdated": (
                    thread_status.get("thread_outdated")
                    if thread_status is not None
                    else None
                ),
                "body": body,
                "excerpt": body_excerpt(body),
                "ai_prompts": extract_ai_prompts(body),
            }
        )
    return normalized


def collect_paginated(endpoint: str) -> list[dict[str, Any]]:
    pages = json.loads(run_gh(["api", endpoint, "--paginate", "--slurp"]))
    if not isinstance(pages, list):
        raise RuntimeError(f"Unexpected paginated response from {endpoint}")

    items: list[dict[str, Any]] = []
    for page in pages:
        if not isinstance(page, list):
            raise RuntimeError(f"Unexpected page shape from {endpoint}")
        items.extend(page)
    return items


def head_repository_name(pr_view: dict[str, Any]) -> str | None:
    head_repository = pr_view.get("headRepository") or {}
    name_with_owner = head_repository.get("nameWithOwner")
    if name_with_owner:
        return str(name_with_owner)

    owner = (pr_view.get("headRepositoryOwner") or {}).get("login")
    name = head_repository.get("name")
    if owner and name:
        return f"{owner}/{name}"
    return None


def collect(
    pr: int, include_resolved: bool = False, repo: str | None = None
) -> dict[str, Any]:
    fields = (
        "number,title,url,baseRefName,headRefName,headRefOid,headRepository,"
        "headRepositoryOwner,isCrossRepository"
    )
    pr_view = json.loads(
        run_gh(["pr", "view", str(pr), *repo_args(repo), "--json", fields])
    )
    owner, repo_name = parse_repo_from_pr_url(pr_view["url"])

    top_level_raw = collect_paginated(
        f"repos/{owner}/{repo_name}/issues/{pr}/comments"
    )
    reviews_raw = collect_paginated(f"repos/{owner}/{repo_name}/pulls/{pr}/reviews")
    inline_raw = collect_paginated(f"repos/{owner}/{repo_name}/pulls/{pr}/comments")
    review_thread_status = collect_review_thread_status(owner, repo_name, pr)

    top_level = normalize_top_level(top_level_raw)
    reviews = normalize_reviews(reviews_raw)
    inline_comments = normalize_inline(
        inline_raw,
        review_thread_status=review_thread_status,
        include_resolved=include_resolved,
    )

    all_items = [*top_level, *reviews, *inline_comments]
    source_counts = {
        source: sum(1 for item in all_items if item["source"] == source)
        for source in ("human", "ai_reviewer", "automation", "unknown")
    }

    resolved_inline_total = sum(
        1
        for comment in inline_raw
        if review_thread_status.get(inline_root_comment_id(comment), {}).get(
            "thread_resolved"
        )
        is True
    )
    outdated_inline_total = sum(
        1
        for comment in inline_raw
        if review_thread_status.get(inline_root_comment_id(comment), {}).get(
            "thread_outdated"
        )
        is True
    )

    return {
        "pr": {
            "number": pr_view["number"],
            "title": pr_view["title"],
            "url": pr_view["url"],
            "base_ref": pr_view.get("baseRefName"),
            "head_ref": pr_view.get("headRefName"),
            "head_oid": pr_view.get("headRefOid"),
            "head_repository": head_repository_name(pr_view),
            "is_cross_repository": bool(pr_view.get("isCrossRepository")),
        },
        "counts": {
            "top_level": len(top_level),
            "reviews": len(reviews),
            "inline": len(inline_comments),
            "inline_total": len(inline_raw),
            "inline_resolved": resolved_inline_total,
            "inline_outdated": outdated_inline_total,
            "inline_filtered_out": len(inline_raw) - len(inline_comments),
            "total_items": len(all_items),
            "human_items": source_counts["human"],
            "ai_items": source_counts["ai_reviewer"],
            "automation_items": source_counts["automation"],
            "unknown_items": source_counts["unknown"],
        },
        "filters": {"include_resolved_inline": include_resolved},
        "items": all_items,
    }


def print_text_report(payload: dict[str, Any]) -> None:
    pr = payload["pr"]
    counts = payload["counts"]
    print(f"PR #{pr['number']}: {pr['title']}")
    print(pr["url"])
    print(
        "Counts: "
        f"top-level={counts['top_level']}, "
        f"reviews={counts['reviews']}, "
        f"inline={counts['inline']}, "
        f"inline-total={counts['inline_total']}, "
        f"inline-resolved={counts['inline_resolved']}, "
        f"inline-outdated={counts['inline_outdated']}, "
        f"inline-filtered-out={counts['inline_filtered_out']}, "
        f"human={counts['human_items']}, "
        f"ai={counts['ai_items']}, "
        f"automation={counts['automation_items']}, "
        f"unknown={counts['unknown_items']}"
    )
    print("")

    for index, item in enumerate(payload["items"], start=1):
        source = SOURCE_LABELS.get(item["source"], item["source"])
        location = ""
        if item.get("path"):
            location = f" | {item['path']}:{item.get('line') or ''}"
        print(
            f"{index}. [{item['kind']}] {source} @{item['author']}{location}\n"
            f"   {item.get('excerpt', '')}\n"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="List and normalize PR comments")
    parser.add_argument("--pr", type=int, default=None, help="PR number")
    parser.add_argument(
        "--repo",
        default=None,
        help="GitHub repository in OWNER/REPO form (defaults to current repo)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output complete JSON instead of an excerpt-only text report",
    )
    parser.add_argument(
        "--include-resolved",
        action="store_true",
        help="Include resolved inline review threads (default: unresolved only)",
    )
    args = parser.parse_args()

    try:
        ensure_gh()
        pr = resolve_pr_number(args.pr, repo=args.repo)
        payload = collect(
            pr,
            include_resolved=args.include_resolved,
            repo=args.repo,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print_text_report(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
