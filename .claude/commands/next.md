---
name: next
description: Prioritized work queue sorted by priority labels and VISION.md alignment
allowed-tools: Bash, Read, Grep, Glob, Task
---

# /next Skill

Show a prioritized work queue of open issues, sorted by priority labels and grouped by server/area.

## Usage

```
/next                      # Prioritized queue (excludes in-progress/blocked)
/next --all                # Include in-progress and blocked issues
/next --area jira          # Filter by server area
```

## Workflow

### Step 1: Ensure Labels Exist

Create all lifecycle labels idempotently:

```bash
gh label create "priority:critical" --color "B60205" --description "Blocking other work" --force
gh label create "priority:high" --color "D93F0B" --description "Important, should be next" --force
gh label create "priority:medium" --color "FBCA04" --description "Standard priority" --force
gh label create "priority:low" --color "0E8A16" --description "Nice to have" --force
gh label create "in-progress" --color "6F42C1" --description "Actively being worked on" --force
gh label create "ready-for-review" --color "0075CA" --description "PR submitted" --force
gh label create "blocked" --color "9E9E9E" --description "Blocked by something" --force
```

### Step 2: Fetch Data (parallel)

**A — All open issues:**
```bash
gh issue list --state open --limit 100 --json number,title,labels,assignees,body
```

**B — VISION.md direction areas:**
Read `VISION.md` and extract direction areas: Jira, Confluence, Bitbucket, Shared Infrastructure.

**C — In-progress and blocked:**
```bash
gh issue list --label "in-progress" --state open --json number,title,labels,assignees
gh issue list --label "blocked" --state open --json number,title,labels,assignees
```

### Step 3: Categorize Each Issue

1. **Priority** from `priority:*` labels (default: medium)
2. **Area** from keywords:
   - Jira: jira, issue, JQL, board, sprint, workflow, agile
   - Confluence: confluence, page, space, CQL, wiki, blog
   - Bitbucket: bitbucket, repo, PR, pull request, branch, commit, diff
   - Shared: CI, docs, auth, config, shared, monorepo
3. **Status**: in-progress, blocked, ready-for-review, or ready
4. **Dependencies**: scan body for "depends on #N" / "blocked by #N"

### Step 4: Filter

- Default: exclude in-progress, blocked, ready-for-review
- `--all`: include everything
- `--area <area>`: filter by area

### Step 5: Display Queue

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📋 Work Queue
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  🔴 Critical
  (none)

  🟠 High
  (none)

📋 Jira
  🟡 #12 — Add issue link types tool
  🟢 #18 — Add bulk transition support

📋 Confluence
  🟡 #15 — Fix empty CQL search
  🟡 #20 — Add content property tools

📋 Bitbucket
  🟡 #22 — Add code search tool
  🟢 #25 — Add default reviewer tools

📋 Shared Infrastructure
  🟡 #28 — Add integration test framework

────────────────────────────────────────────

  🔴 Critical: 0  🟠 High: 0  🟡 Medium: 5  🟢 Low: 2
  📊 Total: 7 issues ready to work

────────────────────────────────────────────
```

### Step 6: Recommend Next Item

```
  ⭐ Recommended: #15 — Fix empty CQL search
     Rationale: Bug fix, no dependencies, affects core functionality.

────────────────────────────────────────────
  👉 Next: /start-work 15
────────────────────────────────────────────
```

Recommendation logic:
1. Highest priority, not blocked, no open dependencies
2. Prefer bugs over features at same priority
3. Prefer lower issue number (older = waiting longer)

### Step 7: Show In-Progress/Blocked (if --all)

```
📋 In Progress
  🔄 #10 — Add webhook management    → assigned to @troylar

📋 Blocked
  🚫 #22 — Code search              → blocked by #15
```

## Guidelines

- Always show `#N — title` for issue references
- Default view should be actionable — only show issues you can start right now
- If 0 issues ready, suggest `/triage --reassess` or `/new-issue`
- Keep display compact — numbers + titles + labels only
