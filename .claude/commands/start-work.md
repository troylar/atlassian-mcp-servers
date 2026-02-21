---
name: start-work
description: Begin work on a GitHub issue — create branch, explore code, plan implementation
allowed-tools: Bash, Read, Edit, Grep, Glob, Task
---

# /start-work Skill

Set up everything needed to begin implementing a GitHub issue.

## Usage

```
/start-work 12                  # Start work on issue #12 (worktree, default)
/start-work 12 --no-worktree    # Start on a branch in the current tree
/start-work 12 --plan-only      # Just create the plan
```

The argument is a GitHub issue number.

By default, work is set up in a **git worktree** — a separate working directory linked to the same repo. Use `--no-worktree` if you prefer a traditional branch.

## Workflow

### Step 1: Fetch and Validate the Issue

```bash
gh issue view <N> --json number,title,body,labels,state,assignees
```

- If closed, warn and ask if they want to proceed
- If assigned to someone else, warn

### Step 1b: Check Assignment and Status

Ensure lifecycle labels exist (idempotent):
```bash
gh label create "in-progress" --color "6F42C1" --description "Actively being worked on" --force
gh label create "ready-for-review" --color "0075CA" --description "PR submitted" --force
gh label create "blocked" --color "9E9E9E" --description "Blocked by something" --force
```

If already in-progress, warn. If confirmed, assign and label:
```bash
gh issue edit <N> --add-assignee @me --add-label "in-progress"
```

### Step 1c: Vision Alignment Check

Read `VISION.md` and evaluate the issue against the product vision. Report alignment.

- If **[FAIL]**: explain, suggest alternatives. Do not create a branch.
- If **[WARN]**: show concern, ask to confirm.
- If **[PASS]**: continue.

### Step 2: Check for Existing Work

```bash
git branch --list "issue-<N>-*"
gh pr list --search "head:issue-<N>" --json number,title,state,headRefName
```

If a branch or PR exists, ask: continue, start fresh, or abort.

### Step 3: Create Branch and Workspace

Branch name: `issue-<N>-<short-description>` (2-4 words, kebab-case, max 50 chars)

If `--plan-only`, skip branch creation.

#### Default: Worktree

```bash
git fetch origin main
git branch issue-<N>-<description> origin/main
git worktree add ../<repo-name>-<N>-<short-description> issue-<N>-<description>
```

Determine which server(s) the issue affects and install dev deps:
```bash
cd ../<repo-name>-<N>-<short-description>/<server> && pip install -e ".[dev]" -q
```

#### With `--no-worktree`: Traditional Branch

```bash
git checkout main && git pull origin main
git checkout -b issue-<N>-<short-description>
```

### Step 4: Deep Code Exploration (parallel agents)

Launch parallel agents to understand the codebase context:

**Agent A — Architecture context (Sonnet):**
1. Read `README.md` and relevant server's source
2. Identify which server(s) and layer(s) this touches (config, client, tools, models)
3. List key files and patterns

**Agent B — Existing implementation (Sonnet):**
1. Read current code for the affected server
2. Understand patterns: how similar tools are implemented
3. Identify integration points and dependencies

**Agent C — Test landscape (Sonnet):**
1. Find test files for the affected modules
2. Understand testing patterns: fixtures, mocking approach
3. Identify what new tests will be needed

### Step 5: Create Implementation Plan

```markdown
## Implementation Plan: #<N> — <title>

### Summary
<1-2 sentences>

### Server(s) Affected
<jira / confluence / bitbucket>

### Files to Create
- `<server>/src/<module>/<path>` — <purpose>
- `<server>/tests/unit/test_<name>.py` — <what it tests>

### Files to Modify
- `<server>/src/<module>/<path>` — <what changes and why>

### Implementation Steps
1. <First thing to do>
2. <Next step>
N. Run tests: `cd <server> && pytest`
N+1. Run lint: `cd <server> && ruff check src/ tests/`

### Testing Strategy
- <What to test>
- <Edge cases>

### Risks & Considerations
- <Anything tricky, Cloud vs DC differences, breaking changes>
```

### Step 6: Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🚀 Ready to Work: #<N> — <title>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  🔀 Branch:     issue-<N>-<description>
  📂 Worktree:   ../<repo>-<N>-<description>
  👤 Assigned:   @<user>
  🏷️ Status:     in-progress
  📋 Plan:       <N> steps across <N> files
  🧪 Tests:      <N> existing, <N> new needed
  🎯 Vision:     ✅ supports <principles>

<The implementation plan>

────────────────────────────────────────────
  👉 Next: cd ../<repo>-<N>-<description> and say "go",
           or adjust the plan
────────────────────────────────────────────
```

## Guidelines

- The plan should be detailed enough for another developer (or Claude session) to follow
- Don't start coding — this skill only sets up context and plan
- If the issue is vague, flag what's unclear and suggest criteria
- If the issue affects Cloud vs Data Center differently, call that out prominently
