---
name: code-review
description: Code review a pull request with security audit and test verification
allowed-tools: Bash, Read, Edit, Grep, Glob, Task, WebFetch
---

# /code-review Skill

Review a pull request for bugs, security issues, pattern compliance, and test results.

## Usage

```
/code-review 12        # Review PR #12
/code-review           # Review PR for current branch
```

## Workflow

### Step 1: Resolve PR Number

If provided, use it. Otherwise:
```bash
gh pr view --json number --jq '.number'
```

### Step 2: Eligibility Check

```bash
gh pr view <PR> --json state,isDraft,author,title,body,reviews
gh api repos/{owner}/{repo}/issues/<PR>/comments --jq '.[].body'
```

Do NOT proceed if:
- PR is closed/merged
- PR is a draft
- PR already has a code review comment (contains "### Code review" AND "Generated with Claude Code")

**Submit-PR detection:** Check for existing validation comment. If found, set `submit_pr_ran = true`.

### Step 2b: PR Size Check

```bash
gh pr diff <PR> --stat | tail -1
```

Under 300 lines → `small_pr = true`.

### Step 3: Gather Context (parallel Haiku agents)

**Agent A — PR summary:** Run `gh pr view <PR>` and `gh pr diff <PR>`. Return summary of changes.

**Agent B — Run unit tests:** For each server with changes, run `cd <server> && pytest -v --tb=short`. Return pass/fail count.

### Step 4: Deep Review (conditional parallel agents)

| Condition | Agents to run |
|-----------|--------------|
| `submit_pr_ran` | #2, #4, #5 |
| `small_pr` | #2, #3, #4 |
| Large standalone | All 6 |

**#1 — Pattern Compliance (Sonnet):** *(skipped when submit_pr_ran)*
- New tools follow decorator + docstring + client pattern
- Dual auth paths handled (Cloud vs DC)
- Error handling follows existing patterns
- Commits follow `type(scope): description (#issue)`

**#2 — Bug Scan (Sonnet):** *(ALWAYS runs)*
- Return values: unchecked None returns?
- Type mismatches: wrong types from JSON API responses?
- Null/empty handling: missing dict keys, empty lists?
- Exception handling: too broad? Swallowed?
- Cloud vs DC: different API paths handled correctly?
- Off-by-one: pagination params, limit/offset?

**#3 — Security Audit (Sonnet):** *(skipped when submit_pr_ran)*
- Hardcoded credentials?
- Auth headers built from config only?
- Input validation on tool parameters?
- Error messages leak auth details?
- `verify=False` in HTTP clients?

**#4 — Historical Context (Haiku):** *(ALWAYS runs, max 15 tool calls)*
- Reverted fixes? Check git log for `fix:` commits
- TODOs in modified areas addressed?
- Breaking assumptions from comments/commit messages?

**#5 — Code Comments and Intent (Sonnet):** *(ALWAYS runs)*
- Invariant violations?
- TODO completion?
- Docstring accuracy?
- Security comments maintained?

**#6 — Vision Alignment (Haiku):** *(skipped when submit_pr_ran)*
- Not an admin tool / sync engine / UI
- New dependencies justified?
- Lean: could this be simpler?

### Step 5: Confidence Scoring (parallel Haiku agents)

For each FAIL item, launch a Haiku agent to verify and score (0-100):
- **0**: False positive
- **25**: Ambiguous
- **50**: Minor
- **75**: Likely real
- **100**: Confirmed with evidence

### Step 6: Filter

Keep only issues scoring 80+.

### Step 7: Display Local Review Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🔍 Code Review — PR #<N>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  🔗 PR:       #<N> — <title>
  📊 Changes:  N files changed, +X -Y

🧪 Tests
  Result:       ✅ / ❌

🔒 Security
  Credentials:  ✅ / ⚠️
  Auth:         ✅ / ⚠️
```

If issues found, list each with file:line, confidence, detail, and suggestion.

### Step 8: Post Review Comment

Post condensed version as PR comment:

```markdown
### Code review

**Tests:** X passed, Y failed
**Security:** PASS / WARN

Found N issues:

1. <description>
<link to file:line>

Generated with [Claude Code](https://claude.ai/code)
```

### Step 9: Final Summary

```
────────────────────────────────────────────
  💬 Review posted to PR #<N>
  🌐 <PR URL>
  👉 Next: address issues, or /commit when ready
────────────────────────────────────────────
```

### Link Format

Links use full SHA and correct repo:
```
https://github.com/troylar/atlassian-mcp-servers/blob/<full-40-char-sha>/path/to/file.py#L10-L15
```

## Notes

- Use `gh` for all GitHub interactions
- Cite and link every issue
- Keep comments brief and actionable
