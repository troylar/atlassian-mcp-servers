# Product Vision Alignment

Before creating issues, planning features, or starting work, check that the proposed work aligns with the product vision in `VISION.md`.

## Quick Reference — Core Principles

1. **One pip install per server** — standalone packages, no shared libraries
2. **Dual-auth by default** — Cloud (Basic) + Data Center (PAT), auto-detected
3. **Complete API coverage** — expose every commonly-used operation
4. **Consistent patterns** — config, client, server, tools architecture across all servers
5. **100% test coverage** — every line of business logic tested
6. **Security is structural** — no hardcoded credentials, auth from env vars only
7. **Lean over sprawling** — each tool does one thing well

## What This Is NOT (Negative Guardrails)

These are identity-level constraints. If a feature makes the project more like any of these, flag it.

- **Not a wrapper library** — MCP servers, not importable Python SDKs
- **Not a monolith** — each server is independent
- **Not an admin tool** — user-level operations only
- **Not a sync engine** — request/response, not background processing
- **Not a UI** — no web or CLI interface, MCP is the interface

## Out of Scope (Hard No)

Do not build or propose features in these areas:
- Atlassian administration APIs
- Webhook receivers or event processing
- Data migration or bulk operations
- Atlassian Marketplace integration
- OAuth authorization code flow

## The Litmus Test

When evaluating a feature idea, ask:
1. Does a typical developer need this operation regularly?
2. Does it work with both Cloud and Data Center?
3. Is it a single, focused operation (not a workflow)?
4. Can it be tested without a live Atlassian instance?
5. Does it follow the existing patterns in the codebase?

If the answer to any of these is "no," flag the concern before proceeding. Read `VISION.md` for the full product vision.

## When Ideas Don't Align

If a user proposes work that conflicts with the vision:
- Don't silently proceed — raise the concern directly
- Explain which principle it conflicts with
- Suggest an alternative approach that aligns, if one exists
- If the user wants to proceed despite the concern: go ahead, but:
  1. Add the `vision-review` label to the issue/PR
  2. Note the specific vision tension in the issue/PR description
