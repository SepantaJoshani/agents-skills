#!/usr/bin/env python3
"""Deterministic tests for list_comments.py."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("list_comments.py")
SPEC = importlib.util.spec_from_file_location("address_pr_comments_list", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ListCommentsTests(unittest.TestCase):
    def test_classifies_sources_without_login_substring_false_positives(self) -> None:
        self.assertEqual(MODULE.classify_source("botanist", "User"), "human")
        self.assertEqual(
            MODULE.classify_source("coderabbitai[bot]", "Bot"), "ai_reviewer"
        )
        self.assertEqual(MODULE.classify_source("vercel", "Bot"), "automation")
        self.assertEqual(
            MODULE.classify_source("custom-review[bot]", None), "automation"
        )
        self.assertEqual(MODULE.classify_source("", None), "unknown")

    def test_normalization_preserves_complete_body(self) -> None:
        body = "x" * 300
        item = MODULE.normalize_top_level(
            [
                {
                    "id": 1,
                    "user": {"login": "reviewer", "type": "User"},
                    "body": body,
                }
            ]
        )[0]

        self.assertEqual(item["source"], "human")
        self.assertEqual(item["body"], body)
        self.assertEqual(len(item["excerpt"]), 220)

    def test_empty_commented_reviews_are_filtered(self) -> None:
        reviews = MODULE.normalize_reviews(
            [
                {
                    "id": 1,
                    "user": {"login": "reviewer", "type": "User"},
                    "body": "",
                    "state": "COMMENTED",
                },
                {
                    "id": 2,
                    "user": {"login": "reviewer", "type": "User"},
                    "body": "",
                    "state": "APPROVED",
                },
                {
                    "id": 3,
                    "user": {"login": "reviewer", "type": "User"},
                    "body": "Please add coverage",
                    "state": "COMMENTED",
                },
            ]
        )

        self.assertEqual([review["id"] for review in reviews], [2, 3])

    def test_inline_replies_inherit_root_thread_status(self) -> None:
        comments = [
            {
                "id": 10,
                "user": {"login": "reviewer", "type": "User"},
                "body": "Root",
            },
            {
                "id": 11,
                "in_reply_to_id": 10,
                "user": {"login": "author", "type": "User"},
                "body": "Reply",
            },
        ]
        statuses = {
            10: {
                "thread_id": "thread-1",
                "thread_resolved": True,
                "thread_outdated": False,
            }
        }

        self.assertEqual(MODULE.normalize_inline(comments, statuses, False), [])
        included = MODULE.normalize_inline(comments, statuses, True)
        self.assertEqual(len(included), 2)
        self.assertTrue(all(item["thread_resolved"] for item in included))

    def test_paginated_rest_responses_are_flattened(self) -> None:
        response = json.dumps([[{"id": 1}], [{"id": 2}]])
        with patch.object(MODULE, "run_gh", return_value=response) as run_gh:
            items = MODULE.collect_paginated("repos/o/r/issues/1/comments")

        self.assertEqual(items, [{"id": 1}, {"id": 2}])
        run_gh.assert_called_once_with(
            [
                "api",
                "repos/o/r/issues/1/comments",
                "--paginate",
                "--slurp",
            ]
        )

    def test_review_threads_follow_every_page(self) -> None:
        pages = [
            {
                "data": {
                    "repository": {
                        "pullRequest": {
                            "reviewThreads": {
                                "nodes": [
                                    {
                                        "id": "thread-1",
                                        "isResolved": False,
                                        "isOutdated": False,
                                        "comments": {"nodes": [{"databaseId": 10}]},
                                    }
                                ],
                                "pageInfo": {
                                    "hasNextPage": True,
                                    "endCursor": "next-page",
                                },
                            }
                        }
                    }
                }
            },
            {
                "data": {
                    "repository": {
                        "pullRequest": {
                            "reviewThreads": {
                                "nodes": [
                                    {
                                        "id": "thread-2",
                                        "isResolved": True,
                                        "isOutdated": True,
                                        "comments": {"nodes": [{"databaseId": 20}]},
                                    }
                                ],
                                "pageInfo": {
                                    "hasNextPage": False,
                                    "endCursor": None,
                                },
                            }
                        }
                    }
                }
            },
        ]

        with patch.object(
            MODULE, "run_gh", side_effect=[json.dumps(page) for page in pages]
        ) as run_gh:
            statuses = MODULE.collect_review_thread_status("owner", "repo", 7)

        self.assertEqual(set(statuses), {10, 20})
        self.assertTrue(statuses[20]["thread_resolved"])
        self.assertEqual(run_gh.call_count, 2)
        self.assertIn("cursor=next-page", run_gh.call_args_list[1].args[0])

    def test_collect_composes_complete_source_aware_payload(self) -> None:
        pr_view = {
            "number": 7,
            "title": "Improve feedback handling",
            "url": "https://github.com/owner/repo/pull/7",
            "baseRefName": "main",
            "headRefName": "fix/feedback",
            "headRefOid": "abc123",
            "headRepository": {"nameWithOwner": "contributor/repo"},
            "headRepositoryOwner": {"login": "contributor"},
            "isCrossRepository": True,
        }
        top_level = [
            {
                "id": 1,
                "user": {"login": "vercel[bot]", "type": "Bot"},
                "body": "deployment status",
            }
        ]
        reviews = [
            {
                "id": 2,
                "user": {"login": "reviewer", "type": "User"},
                "body": "",
                "state": "COMMENTED",
            },
            {
                "id": 3,
                "user": {"login": "coderabbitai[bot]", "type": "Bot"},
                "body": "Automated finding",
                "state": "COMMENTED",
            },
        ]
        inline = [
            {
                "id": 10,
                "user": {"login": "reviewer", "type": "User"},
                "body": "Human finding",
            }
        ]
        statuses = {
            10: {
                "thread_id": "thread-10",
                "thread_resolved": False,
                "thread_outdated": False,
            }
        }

        with patch.object(MODULE, "run_gh", return_value=json.dumps(pr_view)):
            with patch.object(
                MODULE,
                "collect_paginated",
                side_effect=[top_level, reviews, inline],
            ):
                with patch.object(
                    MODULE,
                    "collect_review_thread_status",
                    return_value=statuses,
                ):
                    payload = MODULE.collect(7, repo="owner/repo")

        self.assertEqual(payload["pr"]["head_repository"], "contributor/repo")
        self.assertTrue(payload["pr"]["is_cross_repository"])
        self.assertEqual(payload["counts"]["reviews"], 1)
        self.assertEqual(payload["counts"]["human_items"], 1)
        self.assertEqual(payload["counts"]["ai_items"], 1)
        self.assertEqual(payload["counts"]["automation_items"], 1)
        self.assertEqual(payload["items"][2]["body"], "Human finding")

    def test_prompt_extraction_accepts_fence_languages_and_quotes(self) -> None:
        body = """Prompt for AI Agents

```text
Verify the issue.
```

> In @src/example.py at line 3, fix the issue.
"""
        prompts = MODULE.extract_ai_prompts(body)

        self.assertIn("Verify the issue.", prompts)
        self.assertIn("> In @src/example.py at line 3, fix the issue.", prompts)


if __name__ == "__main__":
    unittest.main()
