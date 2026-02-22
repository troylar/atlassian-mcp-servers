# Jira MCP Server

Model Context Protocol server for Jira — exposes issue tracking, search, boards, sprints, and project management as MCP tools for Cloud and Data Center instances.

## Installation

```bash
pip install atlassian-jira-mcp
```

## Configuration

All configuration is via environment variables. The server auto-detects the authentication mode based on which variables are set.

### Atlassian Cloud

```bash
export JIRA_MCP_URL=https://your-org.atlassian.net
export JIRA_MCP_EMAIL=you@example.com
export JIRA_MCP_TOKEN=your-api-token
```

Generate an API token at: https://id.atlassian.com/manage-profile/security/api-tokens

### Data Center (PAT)

```bash
export JIRA_MCP_URL=https://jira.your-company.com
export JIRA_MCP_TOKEN=your-personal-access-token
```

Generate a PAT in Jira under Profile > Personal Access Tokens.

### Optional Variables

| Variable | Default | Description |
|---|---|---|
| `JIRA_MCP_AUTH_TYPE` | auto | Force auth mode: `cloud` or `pat` |
| `JIRA_MCP_TIMEOUT` | `30` | HTTP request timeout in seconds |
| `JIRA_MCP_VERIFY_SSL` | `true` | Verify SSL certificates |
| `JIRA_MCP_CACHE_TTL` | `3600` | Field schema cache TTL in seconds |

Auth type is auto-detected: if `JIRA_MCP_EMAIL` is set, Cloud (Basic auth) is used; otherwise PAT (Bearer auth) is used. Set `JIRA_MCP_AUTH_TYPE` explicitly to override.

## MCP Client Configuration

Add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "jira": {
      "command": "python",
      "args": ["-m", "jira_mcp_server"],
      "env": {
        "JIRA_MCP_URL": "https://your-org.atlassian.net",
        "JIRA_MCP_EMAIL": "you@example.com",
        "JIRA_MCP_TOKEN": "your-api-token"
      }
    }
  }
}
```

For Data Center, omit `JIRA_MCP_EMAIL`.

## Tools

### Issues

| Tool | Description |
|---|---|
| `jira_issue_create_tool` | Create a new Jira issue with automatic custom field validation |
| `jira_issue_update_tool` | Update an existing Jira issue; only provided fields are updated |
| `jira_issue_get_tool` | Retrieve full details of a single Jira issue including all custom fields |
| `jira_issue_delete_tool` | Delete a Jira issue |
| `jira_issue_link_tool` | Link two Jira issues together |
| `jira_project_get_schema` | Get field schema for a project and issue type for debugging |

### Search

| Tool | Description |
|---|---|
| `jira_search_issues_tool` | Search for Jira issues using multiple criteria (project, assignee, status, priority, labels, dates) |
| `jira_search_jql_tool` | Execute a JQL query directly; supports all JQL operators and ORDER BY |

### Filters

| Tool | Description |
|---|---|
| `jira_filter_create_tool` | Create a new saved filter for reusing complex search queries |
| `jira_filter_list_tool` | List all accessible filters |
| `jira_filter_get_tool` | Get complete filter details by ID |
| `jira_filter_execute_tool` | Execute a saved filter and return matching issues |
| `jira_filter_update_tool` | Update an existing filter; only provided fields are updated |
| `jira_filter_delete_tool` | Delete a filter |

### Workflow

| Tool | Description |
|---|---|
| `jira_workflow_get_transitions_tool` | Get available workflow transitions for an issue |
| `jira_workflow_transition_tool` | Transition an issue through its workflow |

### Comments

| Tool | Description |
|---|---|
| `jira_comment_add_tool` | Add a comment to an issue (supports Jira markup) |
| `jira_comment_list_tool` | List all comments on an issue |
| `jira_comment_update_tool` | Update an existing comment |
| `jira_comment_delete_tool` | Delete a comment |

### Projects

| Tool | Description |
|---|---|
| `jira_project_list_tool` | List all accessible Jira projects |
| `jira_project_get_tool` | Get project details |
| `jira_project_issue_types_tool` | Get available issue types for a project |

### Boards

| Tool | Description |
|---|---|
| `jira_board_list_tool` | List agile boards, optionally filtered by project |
| `jira_board_get_tool` | Get board details |

### Sprints

| Tool | Description |
|---|---|
| `jira_sprint_list_tool` | List sprints for a board, optionally filtered by state (active, closed, future) |
| `jira_sprint_get_tool` | Get sprint details |
| `jira_sprint_issues_tool` | Get issues in a sprint |

### Users

| Tool | Description |
|---|---|
| `jira_user_search_tool` | Search for Jira users by username, email, or display name |
| `jira_user_get_tool` | Get user details |
| `jira_user_myself_tool` | Get current authenticated user details |

### Attachments

| Tool | Description |
|---|---|
| `jira_attachment_add_tool` | Add an attachment to an issue |
| `jira_attachment_get_tool` | Get attachment metadata |
| `jira_attachment_delete_tool` | Delete an attachment |

### Priorities and Statuses

| Tool | Description |
|---|---|
| `jira_priority_list_tool` | List all available Jira priorities |
| `jira_status_list_tool` | List all available Jira statuses |

### Health

| Tool | Description |
|---|---|
| `jira_health_check` | Verify connectivity to Jira instance and validate authentication |

## Development

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=jira_mcp_server --cov-report=term-missing

# Lint
ruff check src tests

# Type check
mypy src
```

## License

MIT
