---
name: generate-commit-message
description: Generate professional git commit messages following cbea.ms guidelines. Outputs plain copy-pasteable commit message text by default.
---

# Generate Commit Message

Generate commit messages following [cbea.ms guidelines](https://cbea.ms/git-commit/).

## Output Format

Plain text commit message in a code block with NO language tag.

The user should be able to copy the entire content directly. Do NOT include:
- `git commit -m` wrapper
- `EOF` or HEREDOC syntax
- `bash` language tag on the code block
- Extra commentary outside the code block

### Short Example

```
Add input validation to form components
```

### Detailed Example

```
Implement input validation for form components

- Create validation utility with reusable validators
- Add validators for email, phone, and text inputs
- Update `Button` and `Input` to use validation
```

## Format: Short vs Detailed

- **Short**: Subject line only
- **Detailed**: Subject + bullet list body (3–6 bullets)

Decide autonomously based on the nature of the change:
- Small, focused changes → short
- Multi-file restructuring, module extraction, or architectural changes → detailed
- Only ask the user if genuinely uncertain

## Workflow

1. Run `git diff --staged --stat` to see staged changes
2. If nothing is staged, ask the user to stage files
3. Analyze `git diff --staged`
4. Generate the commit message based only on staged changes
5. Output the plain commit message in a code block (no language tag)

## Commit Message Rules

1. **Subject line ≤72 chars**
2. **Capitalize subject**
3. **No period at end**
4. **Imperative mood**: "Add feature" not "Added feature"
5. **Blank line** between subject and body
6. **Body lines ≤72 chars**
7. **Backtick code identifiers**: Always wrap component names, hooks, props, and other code references in backticks (e.g. `OrderForm`, `useContainerQuery`)

### Imperative Test

Subject should complete: "If applied, this commit will [subject]"

## Imperative Verbs by Change Type

| Type | Verbs |
|------|-------|
| Feature | Add, Implement, Introduce, Create |
| Fix | Fix, Resolve, Correct |
| Refactor | Refactor, Simplify, Restructure |
| Docs | Document, Update docs |
| Style | Format, Polish, Clean up |
| Test | Add tests, Update tests |
| Chore | Update deps, Configure |

## Context Detection

Infer context from file paths in the staged diff:

- Monorepo app directories (e.g., `apps/<name>/*`) → mention the app name
- Shared packages (e.g., `packages/<name>/*`) → mention the package name
- Test files (`*.test.*`, `*.spec.*`) → "Add tests" / "Update tests"
- Documentation (`*.md`) → "Document" / "Update docs"
- Config files (`.eslintrc`, `tsconfig.json`, etc.) → "Configure" / "Update config"

## Tips

- If changes are too large, suggest splitting into multiple commits
- Keep bullet points action-oriented and concise (3-6 recommended)
- Focus on WHAT and WHY, not HOW
