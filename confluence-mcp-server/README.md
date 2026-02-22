# Confluence MCP Server

An MCP server that exposes Confluence Cloud and Data Center operations as tools for AI assistants.

## Installation

```bash
pip install atlassian-confluence-mcp
```

## Configuration

All configuration is provided through environment variables. The server auto-detects the auth mode: if `CONFLUENCE_MCP_EMAIL` is set, Cloud (Basic) auth is used; otherwise, PAT auth is assumed.

### Atlassian Cloud

```bash
CONFLUENCE_MCP_URL=https://your-org.atlassian.net
CONFLUENCE_MCP_EMAIL=you@example.com
CONFLUENCE_MCP_TOKEN=your-api-token
```

### Data Center (PAT)

```bash
CONFLUENCE_MCP_URL=https://confluence.your-org.com
CONFLUENCE_MCP_TOKEN=your-personal-access-token
```

### Optional Variables

| Variable | Default | Description |
|---|---|---|
| `CONFLUENCE_MCP_AUTH_TYPE` | auto | Force auth mode: `cloud` or `pat` |
| `CONFLUENCE_MCP_TIMEOUT` | `30` | HTTP request timeout in seconds |
| `CONFLUENCE_MCP_VERIFY_SSL` | `true` | Verify SSL certificates |

## MCP Client Configuration

Add the server to your `.mcp.json`:

```json
{
  "mcpServers": {
    "confluence": {
      "command": "python",
      "args": ["-m", "confluence_mcp_server"],
      "env": {
        "CONFLUENCE_MCP_URL": "https://your-org.atlassian.net",
        "CONFLUENCE_MCP_EMAIL": "you@example.com",
        "CONFLUENCE_MCP_TOKEN": "your-api-token"
      }
    }
  }
}
```

## Tools

### Health Check

| Tool | Description |
|---|---|
| `confluence_health_check` | Verify connectivity to Confluence instance |

### Pages

| Tool | Description |
|---|---|
| `confluence_page_get` | Get page details by ID |
| `confluence_page_get_by_title` | Find a page by title within a space |
| `confluence_page_create` | Create a new Confluence page |
| `confluence_page_update` | Update an existing Confluence page |
| `confluence_page_delete` | Delete a Confluence page |
| `confluence_page_move` | Move a page to a new location |
| `confluence_page_copy` | Copy a page to another space |
| `confluence_page_children` | Get child pages of a page |
| `confluence_page_ancestors` | Get ancestor pages (breadcrumb trail) |
| `confluence_page_history` | Get page version history |
| `confluence_page_version` | Get a specific version of a page |
| `confluence_page_restore` | Restore a page to a previous version |

### Search

| Tool | Description |
|---|---|
| `confluence_search` | Search Confluence content by text with optional filters |
| `confluence_search_cql` | Search Confluence using CQL (Confluence Query Language) |

### Spaces

| Tool | Description |
|---|---|
| `confluence_space_list` | List all accessible Confluence spaces |
| `confluence_space_get` | Get space details |
| `confluence_space_create` | Create a new Confluence space |

### Comments

| Tool | Description |
|---|---|
| `confluence_comment_add` | Add a comment to a page |
| `confluence_comment_list` | List comments on a page |
| `confluence_comment_update` | Update a comment |
| `confluence_comment_delete` | Delete a comment |

### Attachments

| Tool | Description |
|---|---|
| `confluence_attachment_add` | Add an attachment to a page |
| `confluence_attachment_list` | List attachments on a page |
| `confluence_attachment_get` | Get attachment metadata |
| `confluence_attachment_delete` | Delete an attachment |

### Labels

| Tool | Description |
|---|---|
| `confluence_label_add` | Add a label to a page |
| `confluence_label_remove` | Remove a label from a page |
| `confluence_label_get` | Get all labels on a page |

### Blog Posts

| Tool | Description |
|---|---|
| `confluence_blog_create` | Create a blog post |
| `confluence_blog_list` | List blog posts in a space |
| `confluence_blog_get` | Get blog post details |
| `confluence_blog_update` | Update a blog post |
| `confluence_blog_delete` | Delete a blog post |

### Permissions

| Tool | Description |
|---|---|
| `confluence_permissions_get` | Get page restrictions/permissions |
| `confluence_permissions_set` | Set page restrictions/permissions |

### Users

| Tool | Description |
|---|---|
| `confluence_user_get` | Get user details by account ID |
| `confluence_user_current` | Get current authenticated user details |

### Content

| Tool | Description |
|---|---|
| `confluence_content_convert` | Convert content between representations (storage, editor, view, wiki) |
| `confluence_content_from_markdown` | Convert markdown to Confluence storage format (XHTML) |
| `confluence_macro_render` | Render a Confluence macro as storage-format XHTML |

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=confluence_mcp_server --cov-report=term-missing

# Lint
ruff check .

# Format
black .

# Type check
mypy src/
```

## License

MIT
