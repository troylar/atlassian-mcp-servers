---
name: new-issue
description: Create a well-structured GitHub issue from a feature idea or bug report
allowed-tools: Bash, Read, Grep, Glob, Task
---

# /new-issue Skill

Turn a feature idea, bug report, or task description into a structured GitHub issue.

## Usage

```
/new-issue add Jira issue link types tool
/new-issue the Confluence page search returns 500 when CQL is empty
/new-issue add webhook management tools for Bitbucket
```

The argument is a natural-language description of the work. It can be a sentence, a paragraph, or bullet points.

## Workflow

### Step 1: Vision Alignment Check

Before anything else, evaluate the idea against the product vision.

1. Read `VISION.md` for the full product vision
2. Check against **"What This Is NOT"** negative guardrails
3. Check against **Out of Scope** (hard no)
4. Run the **Litmus Test**
5. Identify which **Core Principles** the idea supports

**Report the alignment:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🎯 Vision Alignment
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Supports:     <which core principles>
  Guardrails:   ✅ / ⚠️ <any concerns>
  Scope:        ✅ / ❌ <if it hits an out-of-scope area>
  Litmus test:  ✅ / ⚠️ <flag any concerns>

────────────────────────────────────────────
```

- If the idea **conflicts** (❌): explain, suggest alternative, ask how to proceed.
- If **warnings** (⚠️): explain, confirm. If they proceed, issue gets `vision-review` label.
- If **aligns** (✅): proceed to Step 2.

### Step 2: Understand the Request

Parse the user's input to determine:
- **Type**: `enhancement` (new feature), `bug` (something broken), `documentation`, `testing`, `refactor`
- **Server**: jira, confluence, bitbucket, or shared/ci
- **Urgency**: Is this blocking other work?

### Step 3: Explore Relevant Code (Sonnet agent)

Launch a Sonnet agent to understand the codebase context:

1. Read `README.md` and the relevant server's source files
2. Find related modules, functions, tool definitions
3. Identify:
   - Which files will likely need changes
   - What existing patterns to follow
   - Related existing issues: `gh issue list --search "<keywords>" --json number,title,state --limit 5`

### Step 4: Check for Duplicates

```bash
gh issue list --search "<keywords>" --state all --json number,title,state,labels --limit 10
```

If a duplicate exists, show it and ask if they want to proceed, update it, or skip.

### Step 5: Draft the Issue

```markdown
## Description

<1-3 sentences explaining what and why>

## Context

<Current state — what exists today, what's missing or broken>

## Affected Files

- `<server>/src/<module>/<path>` — <what changes here>
- `<server>/tests/unit/<path>` — <new or modified tests>

## Acceptance Criteria

- [ ] <Specific, testable criterion>
- [ ] <Another criterion>
- [ ] Tests pass: `cd <server> && pytest`
- [ ] Lint passes: `cd <server> && ruff check src/ tests/`
- [ ] 100% coverage maintained

## Implementation Notes

<Optional: suggested approach, patterns to follow>
```

### Step 6: Determine Labels

Assign labels based on type:
- `enhancement` — new feature or capability
- `bug` — something broken
- `documentation` — docs-only changes
- `testing` — test additions
- `refactor` — restructuring without behavior change

Check which labels exist: `gh label list --json name --jq '.[].name'`

Only use labels that exist. Don't create new labels.

### Step 7: Create the Issue

Show preview. Once confirmed:
```bash
gh issue create --title "<title>" --label "<label>" --body "$(cat <<'EOF'
<body content>
EOF
)"
```

### Step 8: Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📋 Issue Created
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  🔗 Issue:    #<N> — <title>
  🏷️ Labels:   <labels>
  🌐 URL:      <url>
  🎯 Vision:   ✅ supports <principles>

────────────────────────────────────────────
  👉 Next: /start-work <N>
────────────────────────────────────────────
```

## Guidelines

- **Title**: imperative mood, concise, under 70 characters
- **Body**: written for a contributor who knows the codebase but not the specific context
- **Acceptance criteria**: specific and testable
- **Don't over-specify**: skip implementation notes if the approach is obvious
