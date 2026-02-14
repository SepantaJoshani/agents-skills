# Agent Skills

A collection of open-source agent skills for AI coding assistants, published on [skills.sh](https://skills.sh).

## Install

Install all skills:

```bash
npx skills add SepantaJoshani/agents-skills
```

Install a specific skill:

```bash
npx skills add SepantaJoshani/agents-skills --skill address-pr-comments
npx skills add SepantaJoshani/agents-skills --skill generate-commit-message
```

This works with 35+ agents including Claude Code, Cursor, Codex, Gemini CLI, GitHub Copilot, and more.

## Skills

| Skill | Description |
|-------|-------------|
| [address-pr-comments](https://skills.sh/SepantaJoshani/agents-skills/address-pr-comments) | Address GitHub PR review comments — triage human + AI bot feedback, validate each comment, apply fixes, and report what was addressed vs rejected. |
| [generate-commit-message](https://skills.sh/SepantaJoshani/agents-skills/generate-commit-message) | Generate professional git commit messages following [cbea.ms](https://cbea.ms/git-commit/) guidelines. |

## Usage

After installing, invoke a skill directly from your agent:

- **Claude Code**: type `/address-pr-comments` or `/generate-commit-message`, or describe the task and the agent auto-selects it
- **Other agents**: the skill loads automatically based on your prompt

## Tips

**Auto-reply to PR comments**: After the agent addresses comments, you can ask it to also post replies on the resolved ones — e.g., *"reply to each addressed comment with what you changed and the commit hash"*. This closes the feedback loop directly in the PR without manual follow-up.

**Pair with a commit message skill**: The `address-pr-comments` skill creates one commit per resolved comment. It automatically picks up any installed commit message skill — whether it's `generate-commit-message` from this repo, your own, or any other you prefer. No skill installed? It falls back to reading your recent `git log` and matching your repo's existing style. You can also tweak the commit section in the SKILL.md after install to enforce your own conventions.

## Requirements

- [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated (for `address-pr-comments`)
- Python 3.8+ (for `address-pr-comments`)

## License

[Apache-2.0](LICENSE)
