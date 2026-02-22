# Bitbucket MCP Server

MCP server for Bitbucket, supporting both Bitbucket Cloud and Bitbucket Data Center.

## Installation

```bash
pip install atlassian-bitbucket-mcp
```

## Configuration

Authentication is auto-detected from environment variables. Set the variables for your deployment type.

### Bitbucket Cloud (Basic Auth)

```bash
export BITBUCKET_MCP_URL="https://api.bitbucket.org"
export BITBUCKET_MCP_EMAIL="you@example.com"
export BITBUCKET_MCP_TOKEN="your-app-password"
export BITBUCKET_MCP_WORKSPACE="your-workspace-slug"
```

### Bitbucket Data Center (PAT)

```bash
export BITBUCKET_MCP_URL="https://bitbucket.your-company.com"
export BITBUCKET_MCP_TOKEN="your-personal-access-token"
```

### Optional Variables

| Variable | Default | Description |
|---|---|---|
| `BITBUCKET_MCP_AUTH_TYPE` | auto | Force auth type: `cloud` or `pat` |
| `BITBUCKET_MCP_TIMEOUT` | `30` | Request timeout in seconds |
| `BITBUCKET_MCP_VERIFY_SSL` | `true` | Verify TLS certificates |

## MCP Client Configuration

Add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "bitbucket": {
      "command": "atlassian-bitbucket-mcp",
      "env": {
        "BITBUCKET_MCP_URL": "https://api.bitbucket.org",
        "BITBUCKET_MCP_EMAIL": "you@example.com",
        "BITBUCKET_MCP_TOKEN": "your-app-password",
        "BITBUCKET_MCP_WORKSPACE": "your-workspace-slug"
      }
    }
  }
}
```

## Tools

### Health

| Tool | Description |
|---|---|
| `bitbucket_health_check` | Verify connectivity to Bitbucket instance |

### Projects

| Tool | Description |
|---|---|
| `bitbucket_project_list` | List Bitbucket projects |
| `bitbucket_project_get` | Get project details |
| `bitbucket_project_create` | Create a new project |

### Repositories

| Tool | Description |
|---|---|
| `bitbucket_repo_list` | List repositories in a project |
| `bitbucket_repo_get` | Get repository details |
| `bitbucket_repo_create` | Create a new repository |
| `bitbucket_repo_delete` | Delete a repository |
| `bitbucket_repo_fork` | Fork a repository |

### Branches

| Tool | Description |
|---|---|
| `bitbucket_branch_list` | List branches in a repository |
| `bitbucket_branch_create` | Create a new branch |
| `bitbucket_branch_delete` | Delete a branch |
| `bitbucket_branch_default` | Get the default branch of a repository |

### Commits

| Tool | Description |
|---|---|
| `bitbucket_commit_list` | List commits in a repository |
| `bitbucket_commit_get` | Get commit details |
| `bitbucket_commit_diff` | Get diff for a commit |

### Pull Requests

| Tool | Description |
|---|---|
| `bitbucket_pr_list` | List pull requests |
| `bitbucket_pr_get` | Get pull request details |
| `bitbucket_pr_create` | Create a pull request |
| `bitbucket_pr_update` | Update a pull request |
| `bitbucket_pr_merge` | Merge a pull request |
| `bitbucket_pr_decline` | Decline a pull request |
| `bitbucket_pr_reopen` | Reopen a declined pull request |
| `bitbucket_pr_diff` | Get pull request diff |
| `bitbucket_pr_commits` | Get commits in a pull request |
| `bitbucket_pr_activities` | Get pull request activity log |

### PR Comments

| Tool | Description |
|---|---|
| `bitbucket_pr_comment_add` | Add a comment to a pull request (supports inline comments) |
| `bitbucket_pr_comment_list` | List comments on a pull request |
| `bitbucket_pr_comment_update` | Update a PR comment |
| `bitbucket_pr_comment_delete` | Delete a PR comment |

### PR Reviews

| Tool | Description |
|---|---|
| `bitbucket_pr_approve` | Approve a pull request |
| `bitbucket_pr_unapprove` | Remove approval from a pull request |
| `bitbucket_pr_needs_work` | Mark a pull request as needs work (Data Center only) |

### Files

| Tool | Description |
|---|---|
| `bitbucket_file_browse` | Browse files in a repository |
| `bitbucket_file_content` | Get file content |

### Tags

| Tool | Description |
|---|---|
| `bitbucket_tag_list` | List tags in a repository |
| `bitbucket_tag_create` | Create a tag |
| `bitbucket_tag_delete` | Delete a tag |

### Webhooks

| Tool | Description |
|---|---|
| `bitbucket_webhook_list` | List webhooks on a repository |
| `bitbucket_webhook_create` | Create a webhook |
| `bitbucket_webhook_delete` | Delete a webhook |

### Build Status

| Tool | Description |
|---|---|
| `bitbucket_build_status_get` | Get build status for a commit |
| `bitbucket_build_status_set` | Set build status for a commit |

### Diffs

| Tool | Description |
|---|---|
| `bitbucket_diff` | Get diff between two refs (branches, commits, tags) |

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=bitbucket_mcp_server --cov-report=term-missing

# Lint
ruff check src tests

# Type check
mypy src
```

## License

MIT
