---
name: submit-pr
description: Validate, audit, and create a pull request with full pre-submission checks
allowed-tools: Bash, Read, Edit, Grep, Glob, Task
---

# /submit-pr Skill

Run a full validation suite on the current branch and create a pull request.

## Usage

```
/submit-pr                          # Submit PR against main
/submit-pr --skip-checks            # Skip validation (not recommended)
/submit-pr --draft                  # Create as draft PR
/submit-pr --checks-only            # Run all checks but don't create the PR
```

## Workflow

### Step 1: Pre-flight (parallel)

**A — Branch status:**
```bash
git branch --show-current
git status --short
git log --oneline main..HEAD
```

**B — Remote status:**
```bash
git remote -v
git rev-list --left-right --count main...HEAD
```

**C — Merge conflicts:**
```bash
git merge-tree $(git merge-base main HEAD) main HEAD
```

Verify: on feature branch, commits ahead, no uncommitted changes, can merge cleanly.

### Step 2: Extract Issue References

From branch name and commits:
```bash
git branch --show-current
git log --oneline main..HEAD
```

- Extract `#N` references and issue number from branch name
- Verify each exists: `gh issue view <N> --json state,title`
- Primary issue (from branch) gets `Closes #N`
- If NO references found, abort.

### Step 3: Code Quality (parallel, unless --skip-checks)

For each server with changes, run in parallel:

**A — Lint:**
```bash
cd <server> && ruff check src/ tests/ 2>&1 | tail -30
```

**B — Unit tests:**
```bash
cd <server> && pytest -v --tb=short 2>&1 | tail -80
```

**C — Type check:**
```bash
cd <server> && mypy src/ 2>&1 | tail -30
```

These are **blocking** — if any fail, abort.

### Step 4: Test Coverage for New Code

Check that new/modified source files have corresponding tests:

```bash
git diff --name-only --diff-filter=AM main..HEAD -- '*.py'
```

For each source file, verify a test file exists. Flag missing tests.

### Step 5: Deep Analysis (parallel agents, unless --skip-checks)

Launch 4 parallel agents:

**Agent A — Test Thoroughness (Sonnet):**
- Every public function has at least one test
- Both happy path and error paths covered
- HTTP mocking for all API calls
- Cloud and Data Center paths tested separately

**Agent B — Pattern Compliance (Sonnet):**
- Commit messages follow `type(scope): description (#issue)`
- New tools follow existing patterns (decorator, docstring, client usage)
- Security patterns followed (no hardcoded credentials, proper error handling)

**Agent C — Documentation Freshness (Haiku, authoritative — applies fixes):**
- README.md: new tools documented? Server descriptions current?
- Each server's README: tool list current?
- Apply fixes directly.

**Agent D — Security Scan (Sonnet):**
- No hardcoded credentials or tokens
- Auth headers built from config only
- Input validation on tool parameters
- Error messages don't leak auth details
- No `verify=False` in HTTP clients

### Step 6: Commit Documentation Fixes

If Agent C applied doc updates, stage and commit them.

### Step 7: GitHub Issue Check

Verify all commits reference valid issues.

### Step 8: Display Validation Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🔍 PR Validation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  🔀 Target:   <branch> → main
  📊 Commits:  N commits, M files changed

📋 Branch Status
  Uncommitted:    ✅ / ⚠️
  Merge:          ✅ / ⚠️
  Issues:         ✅ / ⚠️

📋 Code Quality
  Lint:           ✅ / ❌
  Tests:          ✅ / ❌ (per server)
  Type Check:     ✅ / ❌

🧪 Test Coverage
  Test Files:     ✅ / ❌

🔒 Security
  Credentials:    ✅ / ⚠️
  Auth patterns:  ✅ / ⚠️

📖 Documentation
  README.md:      ✅ / ⚠️

────────────────────────────────────────────
  ✅ Result: READY  /  ❌ Result: NOT READY
────────────────────────────────────────────
```

If `--checks-only`, stop here. If NOT READY, abort.

### Step 9: Generate PR Description

```markdown
## Summary

<2-4 bullet points>

## Changes

### <Server>
- `file.py` — <what changed>

## Issue References

Closes #<N>

## Test Plan

- [ ] Tests pass: `cd <server> && pytest`
- [ ] Lint passes: `cd <server> && ruff check src/ tests/`
- [ ] 100% coverage maintained
- [ ] <Specific test scenarios>

---
Generated with [Claude Code](https://claude.ai/code)
```

### Step 10: Push and Create PR

```bash
git push -u origin $(git branch --show-current)
gh pr create --title "<title>" --body "$(cat <<'EOF'
<body>
EOF
)"
```

### Step 10b: Transition Issue Labels

```bash
gh issue edit <N> --remove-label "in-progress" --add-label "ready-for-review"
```

### Step 11: Automatic Code Review

Run `/code-review` on the new PR. If issues found, offer to fix (max 2 rounds).

### Step 12: Final Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🚀 PR Created
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  🔗 PR:       #<N> — <title>
  🌐 URL:      <url>
  📎 Issues:   Closes #<N>
  🧪 Checks:   ✅ lint, tests, types
  🔒 Security: ✅
  🎯 Vision:   ✅

────────────────────────────────────────────
  👉 Next: wait for CI, or request human review
────────────────────────────────────────────
```

## Guidelines

- Never create a PR without at least one issue reference
- Never create a PR with failing tests
- Keep PR title concise — details in the body
- If PR is large (>500 lines), suggest breaking it up
