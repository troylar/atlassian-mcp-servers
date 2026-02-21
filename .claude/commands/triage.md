---
name: triage
description: Set or reassess priority on issues against VISION.md
allowed-tools: Bash, Read, Grep, Glob, Task
---

# /triage Skill

Set priority on individual issues or reassess all open issues against VISION.md.

## Usage

```
/triage 12 high                          # Set priority on issue #12
/triage 12 critical
/triage 12 blocked "waiting on #15"      # Mark as blocked
/triage 12 unblock                       # Remove blocked
/triage --reassess                       # Full reassessment
```

## Workflow — Single Issue Mode

### Step 1: Ensure Labels Exist

```bash
gh label create "priority:critical" --color "B60205" --description "Blocking other work" --force
gh label create "priority:high" --color "D93F0B" --description "Important, should be next" --force
gh label create "priority:medium" --color "FBCA04" --description "Standard priority" --force
gh label create "priority:low" --color "0E8A16" --description "Nice to have" --force
gh label create "in-progress" --color "6F42C1" --description "Actively being worked on" --force
gh label create "ready-for-review" --color "0075CA" --description "PR submitted" --force
gh label create "blocked" --color "9E9E9E" --description "Blocked by something" --force
```

### Step 2: Fetch and Update

```bash
gh issue view <N> --json number,title,labels,body,state
```

Remove all `priority:*` labels, add new one. For blocked: add label + comment. For unblock: remove label + comment.

### Step 3: Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🏷️ Triage: #<N> — <title>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Previous:  🟡 medium
  Updated:   🟠 high

────────────────────────────────────────────
  👉 Next: /next to see the updated queue
────────────────────────────────────────────
```

---

## Workflow — Reassess Mode (`--reassess`)

### Step 1: Ensure Labels Exist

Same as single issue mode.

### Step 2: Fetch All Data (parallel)

**A — Open issues:** `gh issue list --state open --limit 100 --json number,title,labels,body,assignees`

**B — VISION.md:** Read and extract direction areas (Jira, Confluence, Bitbucket, Shared Infrastructure).

**C — Recent closed:** `gh issue list --state closed --limit 20 --json number,title,labels,closedAt`

### Step 3: Evaluate Each Issue

Launch a Sonnet agent to evaluate all issues:
1. **Vision alignment** — which direction area?
2. **Type** — bug, enhancement, refactor, documentation, testing
3. **Impact** — how many users/use cases affected?
4. **Effort** — small/medium/large
5. **Dependencies** — blocks/blocked by?
6. **Suggested priority:** critical, high, medium, low

### Step 4: Display Proposed Changes

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🏷️ Triage Reassessment
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| #   | Title                            | Current | Proposed | Area       |
|-----|----------------------------------|---------|----------|------------|
| 12  | Add Jira issue link tool         | —       | 🟠 high  | Jira       |
| 15  | Fix Confluence search empty CQL  | —       | 🟠 high  | Confluence |

────────────────────────────────────────────
  📊 Changes: N to set, M unchanged
────────────────────────────────────────────
```

### Step 5: Prompt and Apply

Options: Apply all / Pick / Skip.

### Step 6: Summary

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ Triage Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  🔴 Critical:  N    🟠 High:    N
  🟡 Medium:    N    🟢 Low:     N

────────────────────────────────────────────
  👉 Next: /next to see the prioritized queue
────────────────────────────────────────────
```

## Guidelines

- Priority indicators: 🔴 Critical, 🟠 High, 🟡 Medium, 🟢 Low
- Don't change priorities on in-progress issues unless specifically targeted
- Blocked is a status, not a priority — issues keep their priority label
