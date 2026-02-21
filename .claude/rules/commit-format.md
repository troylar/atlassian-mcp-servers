# Commit Message Format

Every commit in this repository MUST follow this format:

```
type(scope): description (#issue)
```

## Rules

- **type** must be one of: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
- **scope** must be a server or area: `jira`, `confluence`, `bitbucket`, `ci`, `docs`
- **description** is lowercase, imperative mood, no period at the end
- **#issue** is a valid GitHub issue number — every commit MUST reference one

## Examples

Good:
- `feat(jira): add attachment download tool (#12)`
- `fix(confluence): handle missing page in search results (#15)`
- `test(bitbucket): add PR merge conflict tests (#18)`
- `docs: update root README with auth examples (#20)`
- `chore(ci): add Python 3.13 to test matrix (#22)`

Bad:
- `fixed bug` (no type, scope, or issue)
- `feat: add new feature` (missing issue reference)
- `feat(jira): Add Attachment Tool (#12)` (capitalized description)

## Scope Exception

`docs` and `chore` types may omit scope when the change is project-wide (e.g., README, CI).

## When Creating Commits

Before running `git commit`, verify:
1. The message matches `type(scope): description (#issue)` format
2. The issue number exists: `gh issue view <N> --json state`
3. The scope matches the primary server being changed
4. The type accurately reflects the change (feat = new, fix = bug, etc.)

If the user provides a commit message that doesn't match this format, reformat it. If no issue number is provided, ask for one — do not commit without it.
