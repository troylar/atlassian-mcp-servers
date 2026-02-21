---
name: write-docs
description: Write or update documentation (README, server docs)
allowed-tools: Bash, Read, Edit, Grep, Glob
---

# /write-docs Skill

Write or update documentation for the monorepo or individual servers.

## Arguments

The first argument is the target: `root` (root README), `jira`, `confluence`, `bitbucket`, or a specific file path. Additional text describes what to write or update.

## Usage

```
/write-docs root                    # Update root README.md
/write-docs jira                    # Update jira-mcp-server/README.md
/write-docs confluence              # Update confluence-mcp-server/README.md
/write-docs bitbucket               # Update bitbucket-mcp-server/README.md
```

## Workflow

### 1. Read the Target

If the file exists, read it. If not, create from scratch.

### 2. Read Source Code

Read the corresponding source code for accuracy:

- **Root README**: All three `pyproject.toml` files, `VISION.md`, tool counts from each server
- **Server README**: The server's `server.py` (tool definitions), `config.py` (env vars), `client.py` (API operations), `pyproject.toml` (version, deps)

### 3. Write the Documentation

Follow these conventions:

- **Voice**: Direct, second-person ("you"), active voice
- **Tone**: Professional but approachable. No filler.
- **Opening**: One-sentence summary, then dive in
- **Code examples**: Every concept gets a working example. Use `$ ` prefix for shell commands
- **Structure**:
  - Overview (what the server does)
  - Installation
  - Authentication (Cloud + Data Center examples)
  - MCP Client Configuration (`.mcp.json` snippet)
  - Available Tools (grouped by category, with brief descriptions)
  - Development (test, lint, type check commands)

### 4. Verify

For server READMEs, verify tool names match the actual `@mcp.tool()` decorated functions in `server.py`.

### 5. Cross-Reference

Ensure the root README links to each server's README and vice versa.
