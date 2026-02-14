# AGENTS.md

This file provides guidance to AI coding agents (Claude Code, Codex, Cursor, etc.) when working with code in this repository.

## Repository Purpose

This repository publishes open-source agent skills to [skills.sh](https://skills.sh). Skills are discovered and installed via the `npx skills` CLI, which scans the `skills/` directory for valid `SKILL.md` files.

## Skills Architecture

Each skill follows the [Agent Skills specification](https://agentskills.io/specification):

```
skills/
└── <skill-name>/
    ├── SKILL.md           # Required: YAML frontmatter + markdown instructions
    ├── scripts/           # Optional: Python/Bash executables
    ├── references/        # Optional: Documentation loaded on-demand
    └── assets/            # Optional: Templates, images, etc.
```

### SKILL.md Format

Every `SKILL.md` must have:
- **YAML frontmatter** with `name` (lowercase, hyphens only, must match directory name) and `description` (used by agents to decide when to activate the skill)
- **Markdown body** with instructions the agent follows when the skill is active

The `description` field is critical — it's always in the agent's context and determines auto-invocation.

### Key Constraints

- Keep SKILL.md under 500 lines (move detailed docs to `references/`)
- Directory name must exactly match the `name` field in frontmatter
- Use relative paths (`./scripts/`, `./references/`) for portability across agents
- Generalize for any repository — avoid hardcoded project-specific logic

## Publishing Workflow

1. Create/modify skill in `skills/<skill-name>/`
2. Test locally: `npx skills add .` (installs from local repo)
3. Commit and push to GitHub (repo must be public)
4. Trigger indexing: `npx skills add SepantaJoshani/agents-skills`

Skills.sh automatically indexes via anonymous telemetry — no registration required.

## Testing Skills Locally

Test a skill before publishing:

```bash
# Install from local directory
npx skills add . --skill <skill-name>

# Verify it installed
npx skills list

# Remove after testing
npx skills remove <skill-name>
```

Installed skills appear in `.claude/skills/`, `.cursor/skills/`, etc. depending on detected agents.

## Skill Interdependencies

Skills can reference other skills without hard dependencies. Example pattern from `address-pr-comments`:

> "Examine recent commits (`git log --oneline -10`) to understand the repository's commit message style. If a commit message generation skill is installed, use it. Otherwise, write a concise commit message from the staged diff that follows the same conventions."

This allows skills to work independently while being enhanced when paired.

## Committing Changes

When creating commits in this repository:
1. Check if `generate-commit-message` skill is installed (or any commit message generation skill)
2. If available, use it to generate commit messages
3. If not, examine recent commits (`git log --oneline -10`) to match the repo's style
4. Follow the [cbea.ms](https://cbea.ms/git-commit/) conventions: imperative mood, ≤50 char subject, capitalized, no trailing period

## Requirements

- **GitHub CLI (`gh`)**: Required for `address-pr-comments` skill
- **Python 3.8+**: Required for `address-pr-comments/scripts/list_comments.py`

Skills should document their dependencies in the repo README, not in SKILL.md (which is consumed by agents, not users).
