# Atlassian MCP Servers

A monorepo of [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) servers for Atlassian products, built on [FastMCP 3](https://github.com/jlowin/fastmcp).

| Server | Tools | Package |
|--------|-------|---------|
| [Jira](jira-mcp-server/) | 37 | `atlassian-jira-mcp` |
| [Confluence](confluence-mcp-server/) | 40 | `atlassian-confluence-mcp` |
| [Bitbucket](bitbucket-mcp-server/) | 44 | `atlassian-bitbucket-mcp` |

## Structure

```
atlassian/
├── jira-mcp-server/          # Issues, boards, sprints, workflows
├── confluence-mcp-server/    # Pages, spaces, blogs, search
└── bitbucket-mcp-server/     # Repos, PRs, branches, builds
```

## Installation

Each server is an independent Python package. Install from the server directory:

```bash
cd jira-mcp-server && pip install -e ".[dev]"
cd confluence-mcp-server && pip install -e ".[dev]"
cd bitbucket-mcp-server && pip install -e ".[dev]"
```

Requires Python 3.10+.

## Authentication

All three servers support dual authentication modes, auto-detected from environment variables.

### Atlassian Cloud

Uses Basic auth with your email and an [API token](https://id.atlassian.com/manage-profile/security/api-tokens).

```bash
# Jira Cloud
export JIRA_MCP_URL=https://yoursite.atlassian.net
export JIRA_MCP_EMAIL=you@company.com
export JIRA_MCP_TOKEN=your-api-token

# Confluence Cloud
export CONFLUENCE_MCP_URL=https://yoursite.atlassian.net/wiki
export CONFLUENCE_MCP_EMAIL=you@company.com
export CONFLUENCE_MCP_TOKEN=your-api-token

# Bitbucket Cloud
export BITBUCKET_MCP_URL=https://api.bitbucket.org
export BITBUCKET_MCP_EMAIL=you@company.com
export BITBUCKET_MCP_TOKEN=your-app-password
```

### Self-Hosted (Data Center)

Uses Bearer auth with a [personal access token](https://confluence.atlassian.com/enterprise/using-personal-access-tokens-1026032365.html).

```bash
# Jira Data Center
export JIRA_MCP_URL=https://jira.company.com
export JIRA_MCP_TOKEN=your-personal-access-token

# Confluence Data Center
export CONFLUENCE_MCP_URL=https://confluence.company.com
export CONFLUENCE_MCP_TOKEN=your-personal-access-token

# Bitbucket Data Center
export BITBUCKET_MCP_URL=https://bitbucket.company.com
export BITBUCKET_MCP_TOKEN=your-personal-access-token
```

### Auto-Detection

- If `EMAIL` is set: Cloud mode (Basic auth)
- If only `TOKEN` is set: Data Center mode (Bearer auth)
- Set `AUTH_TYPE=cloud` or `AUTH_TYPE=pat` to override

## MCP Client Configuration

Add to your `.mcp.json` (e.g., for Claude Code):

```json
{
  "mcpServers": {
    "jira": {
      "command": "atlassian-jira-mcp",
      "env": {
        "JIRA_MCP_URL": "https://yoursite.atlassian.net",
        "JIRA_MCP_EMAIL": "you@company.com",
        "JIRA_MCP_TOKEN": "your-api-token"
      }
    },
    "confluence": {
      "command": "atlassian-confluence-mcp",
      "env": {
        "CONFLUENCE_MCP_URL": "https://yoursite.atlassian.net/wiki",
        "CONFLUENCE_MCP_EMAIL": "you@company.com",
        "CONFLUENCE_MCP_TOKEN": "your-api-token"
      }
    },
    "bitbucket": {
      "command": "atlassian-bitbucket-mcp",
      "env": {
        "BITBUCKET_MCP_URL": "https://api.bitbucket.org",
        "BITBUCKET_MCP_EMAIL": "you@company.com",
        "BITBUCKET_MCP_TOKEN": "your-app-password"
      }
    }
  }
}
```

## Development

```bash
# Run tests (from any server directory)
pytest

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

All servers enforce 100% test coverage.

## License

MIT
