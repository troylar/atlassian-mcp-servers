---
name: pr-check
description: Validate an existing PR or remote branch without submitting
allowed-tools: Bash, Read, Edit, Grep, Glob, Task
---

# /pr-check Skill

Run the full validation suite on an **existing PR** or a **remote branch** — without creating or modifying anything. Use this to review someone else's work or re-check your own PR after updates.

For validating and submitting your own branch, use `/submit-pr` instead.

## Usage

```
/pr-check --pr 12                      # Check an existing GitHub PR
/pr-check --branch feature/foo         # Check a local branch (without switching)
/pr-check --worktree /path/to/wt       # Check code in an existing worktree
```

## Workflow

### Step 0: Resolve Target

| Flag | Action | Working directory |
|------|--------|-------------------|
| `--pr <N>` | Fetch PR, create temp worktree | Temp worktree path |
| `--branch <name>` | Create temp worktree from branch | Temp worktree path |
| `--worktree <path>` | Validate path exists | Provided path |

For temp worktrees: create under `<repo-parent>/<repo-name>-pr-check-<id>`.

### Steps 1–7: Full Validation Suite

Run the same validation as `/submit-pr` Steps 1–8 (pre-flight, issue refs, code quality, test coverage, deep analysis, issue check, validation report), but with all commands prefixed with `cd $DIR &&`.

The report format and blocking/warning thresholds are identical.

### Step 8: Cleanup

If a temp worktree was created:
1. Remove worktree: `git worktree remove <path>`
2. Delete temp branch: `git branch -D <branch>`

If `--worktree` was used (user-provided), do NOT remove anything.

### Step 9: Recommendations

```
────────────────────────────────────────────
  👉 Next steps:
    - <if issues found> Request changes on the PR
    - <if clean> Approve and merge
    - <if docs stale> Suggest doc updates to the author
────────────────────────────────────────────
```
