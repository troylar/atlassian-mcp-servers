# Output Formatting

All skill output and reports should be visually striking, scannable, and consistent. Use emoji as status indicators and visual anchors.

## Status Indicators

Use these consistently across all output:
- ✅ `[PASS]` — check passed, no issues
- ❌ `[FAIL]` — check failed, must fix
- ⚠️ `[WARN]` — warning, should review
- ⏭️ `[SKIP]` — check skipped
- 🔄 `[....]` — in progress

## Report Structure

Every skill that produces a report should follow this pattern:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🔍 <Skill Name>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 <Section heading>
  ✅ Check description
  ❌ Check description — details on what failed
  ⚠️ Check description — why this is a warning

📋 <Next section>
  ...

────────────────────────────────────────────
  ✅ Result: READY
  — or —
  ❌ Result: NOT READY — 2 issues to fix
────────────────────────────────────────────

👉 Next steps:
  1. Fix lint error in `jira-mcp-server/src/jira_mcp_server/client.py:45`
  2. Add tests for new `get_issue()` function
  3. Run: `/commit`
```

## Section Icons

Use these emoji as section headers to create visual rhythm:
- 📋 General sections (branch status, code quality)
- 🧪 Test-related sections
- 🔒 Security sections
- 🎯 Vision alignment sections
- 📦 Build/deploy sections
- 📝 Documentation sections
- 🔗 Issue/PR reference sections

## Section Separators

- Use `━━━` (heavy box line) for top/bottom borders of the report
- Use `────` (light box line) for section separators and footer
- Use blank lines between sections for readability

## Tables

When presenting structured data, use aligned markdown tables:

```
| Server     | Tests | Coverage | Status |
|------------|-------|----------|--------|
| Jira       | 422   | 100%     | ✅     |
| Confluence | 161   | 100%     | ✅     |
| Bitbucket  | 242   | 100%     | ✅     |
```

## Summaries

End every skill with a clear, actionable summary. Don't just list results — tell the user what to do next.

## What NOT to Do

- No ASCII art or decorative banners beyond the box-drawing separators
- No walls of text — if output exceeds 40 lines, summarize and offer details on request
- No "Great!" or "Successfully!" preambles — just state what happened
- Don't overuse emoji in prose — they're for status indicators and section headers, not every sentence
