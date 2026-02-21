# Atlassian MCP Servers — Product Vision

## What This Is

A monorepo of Model Context Protocol (MCP) servers that give AI assistants native access to Atlassian products (Jira, Confluence, Bitbucket). Each server is an independent Python package built on FastMCP 3.

## Core Principles

1. **One pip install per server** — Each server is a standalone package. No shared libraries, no monorepo build system, no Docker required.
2. **Dual-auth by default** — Every server works with both Atlassian Cloud (Basic auth) and Data Center (PAT auth), auto-detected from environment variables.
3. **Complete API coverage** — Each server should expose every commonly-used operation for its product. Partial coverage forces users back to the web UI.
4. **Consistent patterns** — All three servers follow the same architecture: config (pydantic-settings), client (httpx), server (FastMCP), tools (decorated functions).
5. **100% test coverage** — Every line of business logic is tested. No exceptions.
6. **Security is structural** — No hardcoded credentials, no eval, no SQL injection vectors. Auth tokens come from environment variables only.
7. **Lean over sprawling** — Each tool does one thing well. Don't add tools for operations nobody uses.

## What This Is NOT

- **Not a wrapper library** — These are MCP servers, not Python SDKs. The interface is MCP tools, not importable functions.
- **Not a monolith** — Each server is independent. You install only what you need.
- **Not an admin tool** — These servers provide user-level operations, not Atlassian administration (user provisioning, license management, etc.).
- **Not a sync engine** — These are request/response tools, not background sync or webhook processors.
- **Not a UI** — No web interface, no CLI interface. The interface is MCP.

## Out of Scope (Hard No)

- Atlassian administration APIs (user management, license management, app management)
- Webhook receivers or event-driven processing
- Data migration or bulk import/export tools
- Atlassian Marketplace integration
- OAuth 2.0 authorization code flow (users provide their own tokens)

## Direction Areas

### Jira
Issue management, search (JQL), boards, sprints, workflows, comments, attachments, projects, users, filters.

### Confluence
Pages, spaces, blogs, search (CQL), comments, attachments, labels, content conversion, permissions, users.

### Bitbucket
Repositories, branches, commits, pull requests (full lifecycle), code review, file browsing, tags, webhooks, build status, diffs, projects.

### Shared Infrastructure
CI/CD, testing infrastructure, documentation, release automation.

## The Litmus Test

When evaluating a new tool or feature:
1. Does a typical developer need this operation regularly?
2. Does it work with both Cloud and Data Center?
3. Is it a single, focused operation (not a workflow)?
4. Can it be tested without a live Atlassian instance?
5. Does it follow the existing patterns in the codebase?
