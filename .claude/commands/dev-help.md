---
name: dev-help
description: Show the developer workflow guide with all available skills and conventions
allowed-tools: Bash, Read, Grep, Glob
---

# /dev-help Skill

Display a comprehensive guide to the developer workflow.

## Workflow

### Step 1: Gather Context

1. List skill files: `ls .claude/commands/`
2. Read `VISION.md` for project overview
3. Check current branch: `git branch --show-current`
4. Recent issues: `gh issue list --limit 5 --json number,title,state`

### Step 2: Display the Guide

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🔌 Atlassian MCP Servers — Developer Guide
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  MCP servers for Jira, Confluence, and Bitbucket.
  Each server: pip install -e ".[dev]" && pytest — that's it.

  📖 Read VISION.md for the full product vision.
  📖 Read README.md for architecture and setup.


🔄 Development Lifecycle
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  📋 Prioritize    →  /next
  🏷️ Triage        →  /triage <issue#> <priority>
  💭 Explore idea  →  /ideate
  💡 Create issue  →  /new-issue
  🚀 Start coding  →  /start-work <issue#>
  💾 Save work     →  /commit
  📤 Submit + review → /submit-pr  (auto-runs /code-review)
  🔍 Review others →  /code-review <pr#>
  📦 Ship          →  /deploy
  🧹 Clean up      →  /cleanup


📋 Skills Reference
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  /ideate <rough idea>
    Explore a feature idea before committing to an issue.
    Checks vision, feasibility, and alternatives.

  /new-issue <description>
    Turn an idea into a structured GitHub issue.

  /start-work <issue#> [--no-worktree]
    Create worktree + branch, explore code, plan implementation.
    Runs 3 parallel agents for deep code exploration.

  /commit
    Stage, validate, and commit with enforced conventions.
    Runs lint + tests on affected server(s).

  /submit-pr [--draft] [--checks-only]
    Full validation + PR creation + auto code review.
    Runs 4 parallel agents: tests, patterns, docs, security.

  /pr-check --pr <N>
    Validate someone else's PR in a temp worktree.

  /code-review [<pr#>]
    Deep review with parallel agents.
    Posts results as PR comment.

  /next [--all] [--area <area>]
    Prioritized work queue by server area.

  /triage <issue#> <priority> | --reassess
    Set priority or reassess all open issues.

  /cleanup [--dry-run]
    Stale branches, orphaned worktrees, stale labels.

  /deploy [patch|minor|major]
    Merge PR, bump version, publish to PyPI.

  /write-docs <target>
    Write or update README documentation.


⚡ Rules (always active)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  📌 No code without a GitHub issue
  📌 Commit format: type(scope): description (#issue)
     Scopes: jira, confluence, bitbucket, ci, docs
  📌 100% test coverage — no exceptions
  📌 Security patterns (OWASP ASVS Level 2)
  📌 Vision alignment checked before work starts
  📌 Consistent output formatting


🎯 Vision Quick Reference
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Core principles:
    1. One pip install per server
    2. Dual-auth by default (Cloud + DC)
    3. Complete API coverage
    4. Consistent patterns across servers
    5. 100% test coverage
    6. Security is structural
    7. Lean over sprawling

  What this is NOT:
    ❌ A wrapper library    ❌ A monolith
    ❌ An admin tool         ❌ A sync engine
    ❌ A UI

  Litmus test:
    → Developer needs it regularly?
    → Works with Cloud and Data Center?
    → Single, focused operation?
    → Testable without live instance?
    → Follows existing patterns?


📂 Project Structure
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  atlassian/
  ├── jira-mcp-server/          # 37 tools
  │   └── src/jira_mcp_server/
  ├── confluence-mcp-server/    # 38 tools
  │   └── src/confluence_mcp_server/
  └── bitbucket-mcp-server/     # 44 tools
      └── src/bitbucket_mcp_server/

  Each server:
    src/<module>/
    ├── server.py       # FastMCP entry + tool definitions
    ├── config.py       # pydantic-settings, dual auth
    ├── client.py       # httpx HTTP client
    ├── models.py       # Pydantic models
    └── tools/          # Tool implementations (Jira only)


────────────────────────────────────────────────────────────
  💡 Tip: Run any skill with no arguments for usage help.
  📖 Full details: VISION.md, README.md
────────────────────────────────────────────────────────────
```
