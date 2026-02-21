---
name: commit
description: Create a well-formatted commit with enforced conventions
allowed-tools: Bash, Read, Grep, Glob
---

# /commit Skill

Create a commit that follows this project's conventions. Validates format, issue references, and test status before committing.

## Usage

```
/commit                              # Auto-detect type, scope, and message
/commit fix(jira): handle empty JQL query (#15)
/commit --amend                      # Amend the last commit (use sparingly)
```

If a message is provided, validate and use it. If no message, generate one from changes.

## Workflow

### Step 1: Assess Changes

Run in parallel:
```bash
git status --short
git diff --cached --stat
git diff --stat
```

- If nothing staged or modified, abort: "Nothing to commit."
- If nothing staged but files modified, show files and ask what to stage.

### Step 2: Determine the Issue Number

Extract from branch name (`issue-<N>-...`):
```bash
git branch --show-current
```

If not found, check recent commits, then ask the user.

Verify: `gh issue view <N> --json state,title --jq '"\(.state): \(.title)"'`

### Step 3: Generate or Validate Message

**If message provided:** Validate `type(scope): description (#N)`:
- type: feat/fix/docs/refactor/test/chore
- scope: jira/confluence/bitbucket/ci/docs
- Issue reference present and matches branch

**If no message:** Generate from diff:
1. Determine type from changes (new files → feat, bug fix → fix, etc.)
2. Determine scope from which server directory has the most changes
3. Draft: `type(scope): description (#N)`

### Step 4: Stage Files

If files aren't staged:
1. Show modified/untracked files
2. Stage relevant files — never `.env`, credentials, or `htmlcov/`
3. Never use `git add -A` or `git add .` — always add specific files

### Step 5: Pre-commit Checks

Get staged Python files:
```bash
git diff --cached --name-only --diff-filter=ACMR -- '*.py'
```

Determine which server(s) have staged files and run checks per server:

```bash
# For each affected server
cd <server> && ruff check <staged files in this server> 2>&1 | tail -20
```

Run tests for affected server(s):
```bash
cd <server> && pytest -x -q 2>&1 | tail -20
```

- If lint fails: auto-fix with `ruff check --fix`, re-stage
- If tests fail: abort. Do not commit with failing tests.

### Step 5b: Complexity Check

Scan staged diff for vision-relevant changes:
1. New dependencies in `pyproject.toml`
2. New environment variables in config
3. Changes affecting auth or client behavior

Report warnings if found (informational, not blocking).

### Step 6: Commit

```bash
git commit -m "$(cat <<'EOF'
type(scope): description (#N)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

### Step 7: Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ Committed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  💬 Message:  type(scope): description (#N)
  🔑 SHA:      <short sha>
  📁 Files:    <N> changed, <N> insertions(+), <N> deletions(-)
  🔗 Issue:    #<N> — <issue title>

  🧪 Checks:   ✅ lint, tests (<N> passed)
  ⚠️ Warnings: <any complexity warnings, or "none">

────────────────────────────────────────────
  👉 Next: <context-aware suggestion>
────────────────────────────────────────────
```

Check for existing PR to determine next step:
- **If PR exists**: `👉 Next: push to update PR #<N>`
- **If no PR**: `👉 Next: /submit-pr when ready`

## Amend Mode

If `--amend`:
1. Show current HEAD commit
2. Confirm with user
3. Use `git commit --amend`
4. Warn if already pushed

## Guidelines

- Never commit without passing tests
- Never commit secrets or `.env` files
- Never use `git add -A` or `git add .`
- One logical change per commit
