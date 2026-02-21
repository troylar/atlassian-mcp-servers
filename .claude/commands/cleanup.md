---
name: cleanup
description: Post-work cleanup — stale branches, orphaned worktrees, unclosed issues, stale labels
allowed-tools: Bash, Read, Grep, Glob, Task
---

# /cleanup Skill

Clean up stale branches, orphaned worktrees, unclosed issues, and stale labels after work is merged.

## Usage

```
/cleanup              # Show report and clean interactively
/cleanup --dry-run    # Show report only, no changes
```

## Workflow

### Step 1: Ensure Labels Exist

Create all lifecycle labels idempotently (same as `/triage`).

### Step 2: Gather State (parallel)

**A — Stale local branches:**
```bash
git branch --list "issue-*"
```
Check each: `gh issue view <N> --json state --jq '.state'`. Stale if CLOSED.

**B — Stale remote branches:**
```bash
git fetch --prune origin
git branch -r --list "origin/issue-*"
```
Check for merged PRs: `gh pr list --head "issue-<N>" --state merged`

**C — Orphaned worktrees:**
```bash
git worktree list --porcelain
```
Orphaned if branch gone or issue closed.

**D — Issues with stale labels:**
```bash
gh issue list --label "in-progress" --state closed --json number,title
gh issue list --label "ready-for-review" --state closed --json number,title
```

**E — Open issues with stale in-progress:**
Check if branch exists for in-progress issues.

### Step 3: Reconcile Merged PRs with Open Issues

```bash
gh pr list --state merged --limit 20 --json number,title,closingIssuesReferences
```

### Step 4: Display Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🧹 Cleanup Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Local Branches to Delete
  issue-12-jira-link-types     → #12 — Add issue link types (CLOSED)

📋 Remote Branches to Prune
  origin/issue-12-jira-link    → PR #14 — feat(jira): add link types (merged)

📋 Worktrees to Remove
  ../atlassian-12-jira-links   → #12 (CLOSED)

📋 Stale Labels to Remove
  #10 — Fix search timeout     → remove `in-progress` (issue closed)

────────────────────────────────────────────
  📊 Summary: N branches, N worktrees, N labels
────────────────────────────────────────────
```

### Step 5: Prompt

If `--dry-run`, stop. Otherwise:
```
  Options:
    → Clean all
    → Pick categories
    → Abort
```

### Step 6: Execute

- Local branches: `git branch -D <branch>`
- Remote branches: `git push origin --delete <branch>`
- Worktrees: `git worktree remove <path> --force`
- Issues: `gh issue close <N> --comment "Closed by /cleanup"`
- Labels: `gh issue edit <N> --remove-label "in-progress"`

### Step 7: Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ Cleanup Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  🔀 Branches deleted:  N local, N remote
  📂 Worktrees removed: N
  🏷️ Labels cleaned:    N

────────────────────────────────────────────
  👉 Next: /next to find your next task
────────────────────────────────────────────
```

## Guidelines

- Always show `#N — title` for issue references
- Never delete without confirmation (unless scripted)
- If worktree has uncommitted changes, warn and skip
